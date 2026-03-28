import SwiftUI

private func runnerBaseRank(_ base: BaseCode) -> Int {
    switch base {
    case .first: return 1
    case .second: return 2
    case .third: return 3
    case .home: return 4
    case .out: return 5
    }
}

struct ContentView: View {
    @StateObject private var store = ScorebookStore()

    var body: some View {
        Group {
            switch store.screen {
            case .home:
                HomeView(
                    onNewGame: { store.showNewGame() },
                    onLoadGame: { store.refreshSavedGames() }
                )
            case .newGame:
                NewGameFlowView(store: store)
            case .loadSaved:
                SavedGamesView(store: store)
            case .game:
                if let session = store.session {
                    GameWorkspaceView(
                        session: session,
                        onBackHome: { store.showHome() },
                        onShowLoad: { store.refreshSavedGames() }
                    )
                } else {
                    HomeView(
                        onNewGame: { store.showNewGame() },
                        onLoadGame: { store.refreshSavedGames() }
                    )
                }
            }
        }
        .alert("Scorebook", isPresented: Binding(
            get: { store.errorMessage != nil },
            set: { if !$0 { store.errorMessage = nil } }
        )) {
            Button("OK", role: .cancel) {
                store.errorMessage = nil
            }
        } message: {
            Text(store.errorMessage ?? "")
        }
    }
}

private struct HomeView: View {
    let onNewGame: () -> Void
    let onLoadGame: () -> Void

    var body: some View {
        NavigationStack {
            VStack(spacing: 28) {
                Spacer()

                VStack(alignment: .leading, spacing: 16) {
                    Text("Baseball Scorebook")
                        .font(.system(size: 42, weight: .bold, design: .rounded))

                    Text("A native iPad scorebook built around an event log, replay-derived state, JSON save files, and scorer-controlled inputs.")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: 760, alignment: .leading)

                HStack(spacing: 16) {
                    Button(action: onNewGame) {
                        Label("New Game", systemImage: "plus.circle.fill")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)

                    Button(action: onLoadGame) {
                        Label("Load Saved Game", systemImage: "folder")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.large)
                }
                .frame(maxWidth: 760)

                Spacer()
            }
            .padding(40)
            .background(
                LinearGradient(
                    colors: [Color(red: 0.95, green: 0.97, blue: 0.92), Color(red: 0.85, green: 0.91, blue: 0.98)],
                    startPoint: .topLeading,
                    endPoint: .bottomTrailing
                )
                .ignoresSafeArea()
            )
        }
    }
}

private struct NewGameFlowView: View {
    @ObservedObject var store: ScorebookStore
    @State private var step: HalfCode = .top

    var body: some View {
        NavigationStack {
            TeamDraftEditorView(
                title: step == .top ? "Away Lineup" : "Home Lineup",
                teamDraft: binding(for: step),
                onGenerate: { store.fillDraft(for: step) },
                onBack: handleBack,
                onContinue: handleContinue
            )
            .navigationTitle("New Game")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Home") {
                        store.showHome()
                    }
                }
            }
        }
    }

    private func binding(for side: HalfCode) -> Binding<TeamDraft> {
        side == .top ? $store.awayDraft : $store.homeDraft
    }

    private func handleBack() {
        if step == .bottom {
            step = .top
        } else {
            store.showHome()
        }
    }

    private func handleContinue() {
        if step == .top {
            step = .bottom
        } else {
            store.startGame()
            step = .top
        }
    }
}

private struct TeamDraftEditorView: View {
    let title: String
    @Binding var teamDraft: TeamDraft
    let onGenerate: () -> Void
    let onBack: () -> Void
    let onContinue: () -> Void

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(title)
                            .font(.largeTitle.bold())
                        Text("Enter the lineup or auto-fill it with deterministic test data.")
                            .foregroundStyle(.secondary)
                    }

                    Spacer()

                    Button("Auto-Generate Lineup", action: onGenerate)
                        .buttonStyle(.bordered)
                }

                TextField("Team name", text: $teamDraft.name)
                    .textFieldStyle(.roundedBorder)
                    .font(.title3)

                Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 10) {
                    GridRow {
                        headerText("Order")
                        headerText("Player")
                        headerText("No.")
                        headerText("Pos")
                    }
                    ForEach($teamDraft.lineup) { $slot in
                        GridRow {
                            Text("\(slot.battingOrder)")
                                .fontWeight(.semibold)
                            TextField("Player \(slot.battingOrder)", text: $slot.playerName)
                                .textFieldStyle(.roundedBorder)
                            TextField("#", text: $slot.playerNumber)
                                .textFieldStyle(.roundedBorder)
                                .frame(width: 90)
                                .keyboardType(.numberPad)
                            Picker("Position", selection: Binding(
                                get: { slot.position ?? .dh },
                                set: { slot.position = $0 }
                            )) {
                                ForEach(Position.allCases) { position in
                                    Text(position.display).tag(position)
                                }
                            }
                            .labelsHidden()
                            .pickerStyle(.menu)
                        }
                    }
                }

                HStack {
                    Button("Back", action: onBack)
                        .buttonStyle(.bordered)
                    Spacer()
                    Button(stepButtonTitle, action: onContinue)
                        .buttonStyle(.borderedProminent)
                }
                .padding(.top, 8)
            }
            .padding(28)
        }
        .background(Color(uiColor: .systemGroupedBackground))
    }

    private var stepButtonTitle: String {
        title == "Away Lineup" ? "Continue to Home" : "Start Game"
    }

    private func headerText(_ text: String) -> some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.secondary)
    }
}

private struct SavedGamesView: View {
    @ObservedObject var store: ScorebookStore

    var body: some View {
        NavigationStack {
            List(store.savedGames) { game in
                Button {
                    store.loadGame(from: game)
                } label: {
                    VStack(alignment: .leading, spacing: 6) {
                        Text(game.title)
                            .font(.headline)
                        Text(game.modifiedAt.formatted(date: .abbreviated, time: .shortened))
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Saved Games")
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Button("Home") {
                        store.showHome()
                    }
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Refresh") {
                        store.refreshSavedGames()
                    }
                }
            }
        }
    }
}

private struct GameWorkspaceView: View {
    @ObservedObject var session: GameSession
    let onBackHome: () -> Void
    let onShowLoad: () -> Void

    @State private var selectedScorecard: HalfCode = .top
    @State private var atBatDraft: AtBatDraft?
    @State private var baserunnerDraft: BaserunnerDraft?
    @State private var substitutionDraft: SubstitutionDraft?
    @State private var showingEndGame = false
    @State private var saveMessage: String?

    var body: some View {
        let snapshot = session.snapshot

        NavigationStack {
            VStack(spacing: 0) {
                if let saveMessage {
                    Text(saveMessage)
                        .font(.footnote.weight(.semibold))
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                        .background(Color.green.opacity(0.18))
                }

                ScrollView {
                    VStack(alignment: .leading, spacing: 20) {
                        ScorelineView(scoreline: snapshot.scoreline)

                        Picker("Scorecard", selection: $selectedScorecard) {
                            Text(snapshot.teams.away.name).tag(HalfCode.top)
                            Text(snapshot.teams.home.name).tag(HalfCode.bottom)
                        }
                        .pickerStyle(.segmented)

                        HStack(alignment: .top, spacing: 20) {
                            ScorecardTeamCardView(
                                teamCard: selectedScorecard == .top ? snapshot.scorecards.away : snapshot.scorecards.home
                            )
                            .frame(maxWidth: .infinity, alignment: .leading)

                            VStack(alignment: .leading, spacing: 16) {
                                StatusPanel(snapshot: snapshot)
                                DefensePanelView(
                                    title: snapshot.teams.away.name,
                                    rows: snapshot.defense.away
                                )
                                DefensePanelView(
                                    title: snapshot.teams.home.name,
                                    rows: snapshot.defense.home
                                )
                                InningTotalsView(title: "\(snapshot.teams.away.name) Totals", totals: snapshot.inningTotals.away)
                                InningTotalsView(title: "\(snapshot.teams.home.name) Totals", totals: snapshot.inningTotals.home)
                                GameLogView(items: snapshot.gameLog)
                            }
                            .frame(width: 340)
                        }
                    }
                    .padding(24)
                }
            }
            .navigationTitle("\(snapshot.teams.away.name) at \(snapshot.teams.home.name)")
            .toolbar {
                ToolbarItemGroup(placement: .topBarLeading) {
                    Button("Home", action: onBackHome)
                    Button("Saved Games", action: onShowLoad)
                }
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button("At Bat") {
                        atBatDraft = session.currentAtBatDraft()
                    }
                    .keyboardShortcut("n", modifiers: [])

                    Button("Runner") {
                        baserunnerDraft = session.currentBaserunnerDraft()
                    }
                    .keyboardShortcut("r", modifiers: [])
                    .disabled(session.currentBaserunnerDraft() == nil)

                    Button("Sub") {
                        substitutionDraft = session.currentSubstitutionDraft()
                    }
                    .keyboardShortcut("s", modifiers: [])

                    Button("Save") {
                        handleSave()
                    }
                    .keyboardShortcut("s", modifiers: [.command])

                    Button("Undo") {
                        session.undo()
                    }
                    .keyboardShortcut("z", modifiers: [.command])

                    Button("Redo") {
                        session.redo()
                    }
                    .keyboardShortcut("y", modifiers: [.command])

                    Button("End Game") {
                        showingEndGame = true
                    }
                    .keyboardShortcut("g", modifiers: [])
                }
            }
            .sheet(item: $atBatDraft) { initialDraft in
                AtBatSheet(initialDraft: initialDraft, battingTeam: snapshot.state.currentHalf == .top ? snapshot.teams.away : snapshot.teams.home) { draft in
                    session.recordAtBat(draft)
                }
            }
            .sheet(item: $baserunnerDraft) { initialDraft in
                BaserunnerSheet(initialDraft: initialDraft) { draft in
                    session.recordBaserunner(draft)
                }
            }
            .sheet(item: $substitutionDraft) { initialDraft in
                SubstitutionSheet(initialDraft: initialDraft) { draft in
                    session.recordSubstitution(draft)
                }
            }
            .sheet(isPresented: $showingEndGame) {
                EndGameSheet(snapshot: snapshot) {
                    session.markCompleted()
                    handleSave()
                    showingEndGame = false
                }
            }
            .overlay(alignment: .top) {
                if let transition = session.pendingTransition {
                    TransitionBanner(transition: transition) {
                        session.dismissTransition()
                    }
                    .padding()
                }
            }
        }
    }

    private func handleSave() {
        do {
            let url = try session.save()
            saveMessage = "Saved \(url.lastPathComponent)"
        } catch {
            saveMessage = "Save failed: \(error.localizedDescription)"
        }
    }
}

private struct StatusPanel: View {
    let snapshot: GameSnapshot

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Status")
                .font(.headline)
            Text("Inning \(snapshot.state.currentInning) \(snapshot.state.currentHalf.shortLabel)")
            Text("Outs: \(snapshot.state.outs)")
            Text("Current Batter: #\(currentBatterOrder(from: snapshot.state)) \(snapshot.currentBatterName)")
            if snapshot.state.runners.isEmpty {
                Text("Bases empty")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(snapshot.state.runners.keys.sorted(by: { runnerBaseRank($0) < runnerBaseRank($1) }), id: \.self) { base in
                    if let runner = snapshot.state.runners[base] {
                        Text("\(base.display): #\(runner.battingOrder)")
                    }
                }
            }
            if snapshot.gameOver {
                Text("Game can be ended.")
                    .fontWeight(.semibold)
                    .foregroundStyle(.green)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct ScorelineView: View {
    let scoreline: Scoreline

    var body: some View {
        ScrollView(.horizontal) {
            Grid(alignment: .leading, horizontalSpacing: 12, verticalSpacing: 8) {
                GridRow {
                    tableHeader("Team")
                    ForEach(scoreline.innings, id: \.self) { inning in
                        tableHeader("\(inning)")
                    }
                    tableHeader("R")
                    tableHeader("H")
                    tableHeader("E")
                }

                teamRow(
                    name: scoreline.awayName,
                    values: scoreline.awayRunsByInning,
                    totals: scoreline.awayTotals,
                    half: .top
                )
                teamRow(
                    name: scoreline.homeName,
                    values: scoreline.homeRunsByInning,
                    totals: scoreline.homeTotals,
                    half: .bottom
                )
            }
            .padding(18)
            .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
        }
    }

    private func teamRow(name: String, values: [Int?], totals: ScorelineTotals, half: HalfCode) -> some View {
        GridRow {
            Text(name)
                .fontWeight(.semibold)
            ForEach(Array(values.enumerated()), id: \.offset) { index, value in
                let inning = scoreline.innings[index]
                Text(value.map(String.init) ?? "—")
                    .frame(minWidth: 28)
                    .padding(.vertical, 6)
                    .background(scoreline.activeInning == inning && scoreline.activeHalf == half ? Color.accentColor.opacity(0.18) : .clear, in: RoundedRectangle(cornerRadius: 8))
            }
            Text("\(totals.runs)")
            Text("\(totals.hits)")
            Text("\(totals.errors)")
        }
    }

    private func tableHeader(_ text: String) -> some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .foregroundStyle(.secondary)
    }
}

private struct ScorecardTeamCardView: View {
    let teamCard: ScorecardTeamCard

    var body: some View {
        ScrollView([.horizontal, .vertical]) {
            VStack(alignment: .leading, spacing: 10) {
                Text(teamCard.teamName)
                    .font(.title2.bold())

                Grid(alignment: .leading, horizontalSpacing: 8, verticalSpacing: 8) {
                    GridRow {
                        Text("#")
                        Text("Player")
                        Text("Pos")
                        ForEach(teamCard.innings, id: \.self) { inning in
                            Text("\(inning)")
                                .frame(width: 84)
                        }
                    }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                    ForEach(teamCard.rows) { row in
                        GridRow(alignment: .top) {
                            Text("\(row.battingOrder)")
                                .fontWeight(.semibold)
                            VStack(alignment: .leading) {
                                Text(row.playerName)
                                Text("#\(row.playerNumber)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Text(row.position)
                            ForEach(Array(row.cells.enumerated()), id: \.offset) { _, cell in
                                if let cell {
                                    ScorecardCellView(cell: cell)
                                        .frame(width: 84, height: 84)
                                } else {
                                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                                        .stroke(Color.secondary.opacity(0.25), style: StrokeStyle(lineWidth: 1, dash: [3, 3]))
                                        .frame(width: 84, height: 84)
                                }
                            }
                        }
                    }
                }
            }
            .padding(20)
        }
        .background(Color(uiColor: .secondarySystemBackground), in: RoundedRectangle(cornerRadius: 24, style: .continuous))
    }
}

private struct ScorecardCellView: View {
    let cell: ScorecardCell

    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .fill(Color(uiColor: .systemBackground))
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.secondary.opacity(0.18), lineWidth: 1)

            GeometryReader { proxy in
                let width = proxy.size.width
                let height = proxy.size.height
                let center = CGPoint(x: width / 2, y: height / 2)
                let top = CGPoint(x: width / 2, y: 16)
                let left = CGPoint(x: 16, y: height / 2)
                let right = CGPoint(x: width - 16, y: height / 2)
                let bottom = CGPoint(x: width / 2, y: height - 16)

                Path { path in
                    path.move(to: top)
                    path.addLine(to: right)
                    path.addLine(to: bottom)
                    path.addLine(to: left)
                    path.closeSubpath()
                }
                .stroke(Color.secondary.opacity(0.18), lineWidth: 1)

                ForEach(Array(cell.segments.enumerated()), id: \.offset) { _, segment in
                    segmentPath(segment, top: top, left: left, right: right, bottom: bottom, center: center)
                        .stroke(segment.state == .scored ? Color.green : Color.accentColor, lineWidth: 3)
                }
            }
            .padding(10)

            VStack(alignment: .leading, spacing: 4) {
                HStack(alignment: .top) {
                    Text(cell.resultDisplay)
                        .font(.caption.bold())
                    Spacer()
                    if !cell.fielders.isEmpty {
                        Text(cell.fielders)
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.secondary)
                    }
                }
                Spacer()
                ForEach(cell.annotations, id: \.self) { annotation in
                    Text(annotation)
                        .font(.system(size: 9, weight: .medium))
                        .padding(.horizontal, 4)
                        .padding(.vertical, 2)
                        .background(Color.orange.opacity(0.16), in: Capsule())
                }
                if !cell.notes.isEmpty {
                    Text(cell.notes)
                        .font(.system(size: 8))
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }
            }
            .padding(10)
        }
    }

    private func segmentPath(_ segment: ScorecardSegment, top: CGPoint, left: CGPoint, right: CGPoint, bottom: CGPoint, center: CGPoint) -> Path {
        func point(for base: BaseCode) -> CGPoint {
            switch base {
            case .home: return bottom
            case .first: return right
            case .second: return top
            case .third: return left
            case .out: return center
            }
        }

        var path = Path()
        path.move(to: point(for: segment.fromBase))
        path.addLine(to: point(for: segment.toBase))
        return path
    }
}

private struct DefensePanelView: View {
    let title: String
    let rows: [DefenseRow]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text(title)
                .font(.headline)
            ForEach(rows) { row in
                HStack {
                    Text(row.position)
                        .fontWeight(.semibold)
                    Spacer()
                    if let number = row.playerNumber {
                        Text("#\(number)")
                            .foregroundStyle(.secondary)
                    }
                    Text(row.playerName)
                }
                .font(.subheadline)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct InningTotalsView: View {
    let title: String
    let totals: InningTotals

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)
            if totals.innings.isEmpty {
                Text("No completed half-innings yet.")
                    .foregroundStyle(.secondary)
            } else {
                Grid(alignment: .leading, horizontalSpacing: 10, verticalSpacing: 8) {
                    GridRow {
                        Text("Stat")
                        ForEach(totals.innings, id: \.self) { inning in
                            Text("\(inning)")
                        }
                        Text("TOT")
                    }
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)

                    ForEach(["R", "H", "E", "LOB"], id: \.self) { stat in
                        GridRow {
                            Text(stat)
                            ForEach(totals.rows[stat] ?? [], id: \.self) { value in
                                Text("\(value)")
                            }
                            Text("\(totals.totals[stat] ?? 0)")
                                .fontWeight(.semibold)
                        }
                    }
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct GameLogView: View {
    let items: [GameLogItem]

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("Game Log")
                .font(.headline)
            if items.isEmpty {
                Text("No events recorded yet.")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(items.suffix(14)) { item in
                    Text(item.text)
                        .font(.footnote.monospaced())
                        .frame(maxWidth: .infinity, alignment: .leading)
                }
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct AtBatSheet: View {
    let battingTeam: Team
    let onSave: (AtBatDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: AtBatDraft

    init(initialDraft: AtBatDraft, battingTeam: Team, onSave: @escaping (AtBatDraft) -> Void) {
        self.battingTeam = battingTeam
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
    }

    var body: some View {
        NavigationStack {
            Form {
                Section("Batter") {
                    Text("#\(draft.battingOrder) \(draft.batterName)")
                    Picker("Result", selection: $draft.resultType) {
                        ForEach(ResultType.allCases) { resultType in
                            Text(resultType.display).tag(resultType)
                        }
                    }
                    .onChange(of: draft.resultType) { _, _ in
                        draft = refreshAtBatDraft(draft, state: snapshotState, battingTeam: battingTeam)
                    }

                    TextField("Fielders", text: $draft.fielders)
                    Stepper("Outs on play: \(draft.outsOnPlay)", value: $draft.outsOnPlay, in: 0...3)
                    if draft.batterReachedVisible {
                        Toggle("Batter reached safely", isOn: $draft.batterReached)
                    }
                    if draft.resultType.batterDefaultBase != nil || draft.batterReached {
                        Picker("Batter destination", selection: Binding(
                            get: { draft.batterDestination ?? .first },
                            set: { draft.batterDestination = $0 }
                        )) {
                            ForEach([BaseCode.first, .second, .third, .home]) { base in
                                Text(base.display).tag(base)
                            }
                        }
                    }
                    Stepper("RBI: \(draft.rbiCount)", value: $draft.rbiCount, in: 0...4)
                    TextField("Notes", text: $draft.notes, axis: .vertical)
                }

                if !draft.runnerAdvances.isEmpty {
                    Section("Runner Advances") {
                        ForEach($draft.runnerAdvances) { $advance in
                            VStack(alignment: .leading, spacing: 8) {
                                Text("\(advance.runnerName) from \(advance.fromBase.display)")
                                    .font(.subheadline.weight(.semibold))
                                Picker("Destination", selection: $advance.toBase) {
                                    ForEach([BaseCode.first, .second, .third, .home, .out]) { base in
                                        Text(base.display).tag(base)
                                    }
                                }
                                .pickerStyle(.segmented)
                            }
                            .padding(.vertical, 4)
                        }
                    }
                }
            }
            .navigationTitle("At Bat")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Record") {
                        onSave(draft)
                        dismiss()
                    }
                }
            }
        }
    }

    private var snapshotState: GameState {
        GameState(
            currentInning: draft.inning,
            currentHalf: draft.half,
            currentBatterIndex: [draft.half: max(draft.battingOrder - 1, 0)],
            outs: 0,
            runners: Dictionary(uniqueKeysWithValues: draft.runnerAdvances.map {
                ($0.fromBase, RunnerInfo(battingOrder: $0.runnerBattingOrder, atBatInning: $0.runnerAtBatInning))
            }),
            awayScore: 0,
            homeScore: 0,
            gameOver: false,
            inningStats: [:]
        )
    }
}

private struct BaserunnerSheet: View {
    let onSave: (BaserunnerDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: BaserunnerDraft

    init(initialDraft: BaserunnerDraft, onSave: @escaping (BaserunnerDraft) -> Void) {
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
    }

    var body: some View {
        NavigationStack {
            Form {
                Picker("From", selection: $draft.fromBase) {
                    ForEach([BaseCode.first, .second, .third]) { base in
                        Text(base.display).tag(base)
                    }
                }
                Picker("To", selection: $draft.toBase) {
                    ForEach([BaseCode.second, .third, .home, .out]) { base in
                        Text(base.display).tag(base)
                    }
                }
                Picker("How", selection: $draft.how) {
                    ForEach(BaserunnerType.allCases) { baserunnerType in
                        Text(baserunnerType.rawValue).tag(baserunnerType)
                    }
                }
                TextField("Fielders", text: $draft.fielders)
            }
            .navigationTitle("Baserunner Event")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Record") {
                        onSave(draft)
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct SubstitutionSheet: View {
    let onSave: (SubstitutionDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: SubstitutionDraft

    init(initialDraft: SubstitutionDraft, onSave: @escaping (SubstitutionDraft) -> Void) {
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
    }

    var body: some View {
        NavigationStack {
            Form {
                Picker("Team", selection: $draft.team) {
                    Text("Away").tag(HalfCode.top)
                    Text("Home").tag(HalfCode.bottom)
                }
                Picker("Batting Order", selection: $draft.battingOrder) {
                    ForEach(1...9, id: \.self) { order in
                        Text("#\(order)").tag(order)
                    }
                }
                TextField("Entering Player", text: $draft.enteringName)
                Stepper("Number: \(draft.enteringNumber)", value: $draft.enteringNumber, in: 0...99)
                Picker("Position", selection: $draft.newPosition) {
                    ForEach(Position.allCases) { position in
                        Text(position.display).tag(position)
                    }
                }
                Picker("Sub Type", selection: $draft.subType) {
                    ForEach(SubType.allCases) { subType in
                        Text(subType.rawValue).tag(subType)
                    }
                }
            }
            .navigationTitle("Substitution")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Record") {
                        onSave(draft)
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct EndGameSheet: View {
    let snapshot: GameSnapshot
    let onConfirm: () -> Void

    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 20) {
                Text(snapshot.gameOver ? "Game over conditions have been reached." : "End this game now and save the current event log?")
                    .font(.title3)
                Text("\(snapshot.teams.away.name) \(snapshot.state.awayScore) - \(snapshot.teams.home.name) \(snapshot.state.homeScore)")
                    .font(.title.bold())
                Spacer()
            }
            .padding(28)
            .navigationTitle("End Game")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save & End") {
                        onConfirm()
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct TransitionBanner: View {
    let transition: TransitionSummary
    let onDismiss: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Completed \(transition.completedHalf.shortLabel) \(transition.completedInning)")
                    .font(.headline)
                Spacer()
                Button("Dismiss", action: onDismiss)
                    .buttonStyle(.bordered)
            }
            Text("\(transition.battingTeam): R \(transition.stats["R", default: 0])  H \(transition.stats["H", default: 0])  E \(transition.stats["E", default: 0])  LOB \(transition.stats["LOB", default: 0])")
            Text("\(transition.score.awayName) \(transition.score.away) - \(transition.score.homeName) \(transition.score.home)")
                .fontWeight(.semibold)
        }
        .padding(18)
        .frame(maxWidth: 460, alignment: .leading)
        .background(.thickMaterial, in: RoundedRectangle(cornerRadius: 22, style: .continuous))
        .shadow(radius: 12)
    }
}
