import Foundation
import Combine

enum AppScreen: Hashable {
    case home
    case newGame
    case loadSaved
    case game
}

struct SavedGameSummary: Hashable, Identifiable {
    var url: URL
    var modifiedAt: Date
    var awayName: String
    var homeName: String

    var id: URL { url }
    var title: String { "\(awayName) at \(homeName)" }
}

@MainActor
final class ScorebookStore: ObservableObject {
    @Published var screen: AppScreen = .home
    @Published var awayDraft: TeamDraft = .empty()
    @Published var homeDraft: TeamDraft = .empty()
    @Published var savedGames: [SavedGameSummary] = []
    @Published var session: GameSession?
    @Published var errorMessage: String?
    @Published var bannerMessage: String?

    func resetDrafts() {
        awayDraft = .empty()
        homeDraft = .empty()
    }

    func showNewGame() {
        resetDrafts()
        screen = .newGame
    }

    func showHome() {
        screen = .home
    }

    func fillDraft(for side: HalfCode) {
        if side == .top {
            awayDraft = LineupTemplates.generate(side: side)
        } else {
            homeDraft = LineupTemplates.generate(side: side)
        }
    }

    func startGame() {
        guard let awayTeam = awayDraft.makeTeam() else {
            errorMessage = "Fill out the entire away lineup before continuing."
            return
        }
        guard let homeTeam = homeDraft.makeTeam() else {
            errorMessage = "Fill out the entire home lineup before continuing."
            return
        }

        session = GameSession(awayTeam: awayTeam, homeTeam: homeTeam)
        screen = .game
        bannerMessage = nil
        errorMessage = nil
    }

    func refreshSavedGames() {
        do {
            savedGames = try ScorebookPersistence.listSavedGames().map { url in
                let values = try? url.resourceValues(forKeys: [.contentModificationDateKey])
                let modifiedAt = values?.contentModificationDate ?? .distantPast
                let loaded = try? ScorebookPersistence.loadGame(url: url)
                return SavedGameSummary(
                    url: url,
                    modifiedAt: modifiedAt,
                    awayName: loaded?.awayTeam.name ?? "Away",
                    homeName: loaded?.homeTeam.name ?? "Home"
                )
            }
            screen = .loadSaved
            errorMessage = nil
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    func loadGame(from summary: SavedGameSummary) {
        do {
            let loaded = try ScorebookPersistence.loadGame(url: summary.url)
            session = GameSession(
                awayTeam: loaded.awayTeam,
                homeTeam: loaded.homeTeam,
                store: loaded.store,
                date: loaded.date,
                stadium: loaded.stadium,
                completed: loaded.completed,
                notes: loaded.notes,
                saveURL: summary.url
            )
            screen = .game
            bannerMessage = "Loaded \(summary.title)."
            errorMessage = nil
        } catch {
            errorMessage = "Unable to load game: \(error.localizedDescription)"
        }
    }
}

@MainActor
final class GameSession: ObservableObject {
    @Published private(set) var awayTeam: Team
    @Published private(set) var homeTeam: Team
    @Published private(set) var store: EventStore
    @Published private(set) var completed: Bool
    @Published var notes: String
    @Published private(set) var pendingTransition: TransitionSummary?
    @Published private(set) var lastSaveURL: URL?

    var date: String
    var stadium: String

    init(
        awayTeam: Team,
        homeTeam: Team,
        store: EventStore = EventStore(),
        date: String = "",
        stadium: String = "",
        completed: Bool = false,
        notes: String = "",
        saveURL: URL? = nil
    ) {
        self.awayTeam = awayTeam
        self.homeTeam = homeTeam
        self.store = store
        self.date = date
        self.stadium = stadium
        self.completed = completed
        self.notes = notes
        self.lastSaveURL = saveURL
    }

    var snapshot: GameSnapshot {
        buildSnapshot(awayTeam: awayTeam, homeTeam: homeTeam, store: store, completed: completed)
    }

    func dismissTransition() {
        pendingTransition = nil
    }

    func currentAtBatDraft() -> AtBatDraft {
        let battingTeam = snapshot.state.currentHalf == .top ? snapshot.teams.away : snapshot.teams.home
        return defaultAtBatDraft(state: snapshot.state, battingTeam: battingTeam)
    }

    func currentBaserunnerDraft() -> BaserunnerDraft? {
        defaultBaserunnerDraft(state: snapshot.state)
    }

    func currentSubstitutionDraft() -> SubstitutionDraft {
        defaultSubstitutionDraft(state: snapshot.state, awayTeam: snapshot.teams.away, homeTeam: snapshot.teams.home)
    }

    func recordAtBat(_ draft: AtBatDraft) {
        let before = snapshot.state
        for event in createAtBatEvents(from: draft, state: before) {
            store.append(event)
        }
        updateTransition(before: before)
    }

    func recordBaserunner(_ draft: BaserunnerDraft) {
        let before = snapshot.state
        guard let event = createBaserunnerEvent(from: draft, state: before) else { return }
        store.append(event)
        updateTransition(before: before)
    }

    func recordSubstitution(_ draft: SubstitutionDraft) {
        let event = createSubstitutionEvent(from: draft, state: snapshot.state, awayTeam: snapshot.teams.away, homeTeam: snapshot.teams.home)
        store.append(event)
    }

    func undo() {
        pendingTransition = nil
        _ = store.undo()
    }

    func redo() {
        pendingTransition = nil
        _ = store.redo()
    }

    func markCompleted() {
        completed = true
    }

    @discardableResult
    func save() throws -> URL {
        let destination: URL
        if let lastSaveURL {
            destination = lastSaveURL
        } else {
            let directory = try ScorebookPersistence.defaultSaveDirectory()
            destination = directory.appendingPathComponent(
                ScorebookPersistence.generateFilename(
                    awayName: awayTeam.name,
                    homeName: homeTeam.name,
                    date: date
                )
            )
        }

        try ScorebookPersistence.saveGame(
            url: destination,
            awayTeam: awayTeam,
            homeTeam: homeTeam,
            store: store,
            date: date,
            stadium: stadium,
            completed: completed,
            notes: notes
        )
        lastSaveURL = destination
        return destination
    }

    private func updateTransition(before: GameState) {
        let after = snapshot.state
        if before.currentHalf != after.currentHalf || before.currentInning != after.currentInning {
            pendingTransition = buildTransitionSummary(
                state: after,
                awayName: snapshot.teams.away.name,
                homeName: snapshot.teams.home.name,
                completedInning: before.currentInning,
                completedHalf: before.currentHalf
            )
        } else {
            pendingTransition = nil
        }
    }
}
