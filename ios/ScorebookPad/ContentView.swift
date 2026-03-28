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
    @State private var cellTapAlertMessage: String?
    @State private var baserunnerEditUndoCount: Int?
    @State private var playerEditDraft: PlayerEditDraft?
    @State private var pendingSubstitution: SubstitutionDraft?
    @State private var showingSubstitutionConfirm = false

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

                VStack(spacing: 0) {
                    VStack(spacing: 12) {
                        Picker("Scorecard", selection: $selectedScorecard) {
                            Text(snapshot.teams.away.name).tag(HalfCode.top)
                            Text(snapshot.teams.home.name).tag(HalfCode.bottom)
                        }
                        .pickerStyle(.segmented)
                        .padding(.horizontal, 24)
                        .padding(.top, 12)
                        .padding(.bottom, 8)
                    }
                    .background(.thinMaterial)

                    ScrollView {
                        VStack(alignment: .leading, spacing: 20) {
                            ScorelineView(scoreline: snapshot.scoreline)

                            HStack(alignment: .top, spacing: 20) {
                                ScorecardTeamCardView(
                                    teamCard: selectedScorecard == .top ? snapshot.scorecards.away : snapshot.scorecards.home,
                                    half: selectedScorecard,
                                    onCellTap: { info in
                                        handleCellTap(info, snapshot: snapshot)
                                    },
                                    onPlayerTap: { battingOrder in
                                        handleSubstitutionTap(half: selectedScorecard, battingOrder: battingOrder, snapshot: snapshot)
                                    },
                                    onPlayerEditTap: { battingOrder in
                                        handlePlayerEditTap(half: selectedScorecard, battingOrder: battingOrder, snapshot: snapshot)
                                    },
                                    onPositionTap: { battingOrder in
                                        handleSubstitutionTap(half: selectedScorecard, battingOrder: battingOrder, snapshot: snapshot)
                                    },
                                    onPositionEditTap: { battingOrder in
                                        handlePlayerEditTap(half: selectedScorecard, battingOrder: battingOrder, snapshot: snapshot)
                                    }
                                )
                                .frame(maxWidth: .infinity, alignment: .leading)

                                VStack(alignment: .leading, spacing: 16) {
                                    StatusPanel(snapshot: snapshot)
                                    DefenseDiamondView(
                                        title: "Opposing Defense",
                                        rows: selectedScorecard == .top ? snapshot.defense.home : snapshot.defense.away
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
                BaserunnerSheet(initialDraft: initialDraft, onEditAtBat: baserunnerEditUndoCount.map { undoCount in
                    {
                        baserunnerDraft = nil
                        DispatchQueue.main.async {
                            handleEditAtBat(undoCount: undoCount)
                        }
                    }
                }) { draft in
                    session.recordBaserunner(draft)
                }
            }
            .sheet(item: $substitutionDraft) { initialDraft in
                SubstitutionSheet(initialDraft: initialDraft, teams: snapshot.teams) { draft in
                    session.recordSubstitution(draft)
                }
            }
            .sheet(item: $playerEditDraft) { draft in
                EditPlayerSheet(initialDraft: draft) { updated in
                    session.updatePlayer(
                        team: updated.team,
                        battingOrder: updated.battingOrder,
                        name: updated.name,
                        number: updated.number,
                        position: updated.position
                    )
                }
            }
            .sheet(isPresented: $showingEndGame) {
                EndGameSheet(snapshot: snapshot) {
                    session.markCompleted()
                    handleSave()
                    showingEndGame = false
                }
            }
            .confirmationDialog("Record Substitution?", isPresented: $showingSubstitutionConfirm, titleVisibility: .visible) {
                Button("Record Substitution") {
                    if let draft = pendingSubstitution {
                        substitutionDraft = draft
                    }
                    pendingSubstitution = nil
                }
                Button("Cancel", role: .cancel) {
                    pendingSubstitution = nil
                }
            } message: {
                if let draft = pendingSubstitution {
                    Text("Substitute in spot #\(draft.battingOrder)?")
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
            .alert("Scorecard", isPresented: Binding(
                get: { cellTapAlertMessage != nil },
                set: { if !$0 { cellTapAlertMessage = nil } }
            )) {
                Button("OK", role: .cancel) {
                    cellTapAlertMessage = nil
                }
            } message: {
                Text(cellTapAlertMessage ?? "")
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

    private func handleCellTap(_ info: ScorecardCellTapInfo, snapshot: GameSnapshot) {
        if let cell = info.cell {
            if let draft = baserunnerDraft(for: cell, state: snapshot.state) {
                baserunnerEditUndoCount = editUndoCount(for: cell, events: session.store.events)
                baserunnerDraft = draft
                return
            }

            if let undoCount = editUndoCount(for: cell, events: session.store.events) {
                baserunnerEditUndoCount = nil
                handleEditAtBat(undoCount: undoCount)
                return
            }

            cellTapAlertMessage = "No active runner found for this cell."
            return
        }

        guard info.half == snapshot.state.currentHalf else {
            cellTapAlertMessage = "Score by the current batting team before filling this cell."
            return
        }

        guard info.inning == snapshot.state.currentInning else {
            cellTapAlertMessage = "Only the current inning can accept new at-bats."
            return
        }

        let currentBatter = currentBatterOrder(from: snapshot.state)
        guard info.battingOrder == currentBatter else {
            cellTapAlertMessage = "This spot is for #\(info.battingOrder). Current batter is #\(currentBatter)."
            return
        }

        baserunnerEditUndoCount = nil
        atBatDraft = session.currentAtBatDraft()
    }

    private func baserunnerDraft(for cell: ScorecardCell, state: GameState) -> BaserunnerDraft? {
        guard let base = state.runners.first(where: { $0.value.battingOrder == cell.battingOrder && $0.value.atBatInning == cell.inning })?.key else {
            return nil
        }

        let destination: BaseCode
        switch base {
        case .first: destination = .second
        case .second: destination = .third
        case .third: destination = .home
        case .home, .out: destination = .out
        }

        return BaserunnerDraft(fromBase: base, toBase: destination, how: .sb, fielders: "")
    }

    private func editUndoCount(for cell: ScorecardCell, events: [GameEvent]) -> Int? {
        var count = 0
        for event in events.reversed() {
            count += 1
            if case let .atBat(atBat) = event {
                guard atBat.inning == cell.inning,
                      atBat.half == cell.half,
                      atBat.battingOrder == cell.battingOrder else {
                    return nil
                }
                return count
            }
        }
        return nil
    }

    private func handleEditAtBat(undoCount: Int) {
        guard undoCount > 0 else { return }
        for _ in 0..<undoCount {
            session.undo()
        }
        baserunnerEditUndoCount = nil
        atBatDraft = session.currentAtBatDraft()
    }

    private func handleSubstitutionTap(half: HalfCode, battingOrder: Int, snapshot: GameSnapshot) {
        pendingSubstitution = substitutionDraft(for: half, battingOrder: battingOrder, snapshot: snapshot)
        showingSubstitutionConfirm = true
    }

    private func handlePlayerEditTap(half: HalfCode, battingOrder: Int, snapshot: GameSnapshot) {
        if let draft = playerEditDraft(for: half, battingOrder: battingOrder, snapshot: snapshot) {
            playerEditDraft = draft
        }
    }

    private func substitutionDraft(for half: HalfCode, battingOrder: Int, snapshot: GameSnapshot) -> SubstitutionDraft {
        var draft = defaultSubstitutionDraft(state: snapshot.state, awayTeam: snapshot.teams.away, homeTeam: snapshot.teams.home)
        draft.team = half
        draft.battingOrder = battingOrder
        draft.newPosition = lookupPosition(for: half, battingOrder: battingOrder, snapshot: snapshot) ?? draft.newPosition
        return draft
    }

    private func playerEditDraft(for half: HalfCode, battingOrder: Int, snapshot: GameSnapshot) -> PlayerEditDraft? {
        let team = half == .top ? snapshot.teams.away : snapshot.teams.home
        guard let slot = team.sortedLineup.first(where: { $0.battingOrder == battingOrder }) else { return nil }
        return PlayerEditDraft(
            team: half,
            battingOrder: battingOrder,
            name: slot.player.name,
            number: slot.player.number,
            position: slot.position
        )
    }

    private func lookupPosition(for half: HalfCode, battingOrder: Int, snapshot: GameSnapshot) -> Position? {
        let team = half == .top ? snapshot.teams.away : snapshot.teams.home
        return team.sortedLineup.first(where: { $0.battingOrder == battingOrder })?.position
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
    let half: HalfCode
    let onCellTap: (ScorecardCellTapInfo) -> Void
    let onPlayerTap: (Int) -> Void
    let onPlayerEditTap: (Int) -> Void
    let onPositionTap: (Int) -> Void
    let onPositionEditTap: (Int) -> Void

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
                            Button {
                                onPlayerTap(row.battingOrder)
                            } label: {
                                VStack(alignment: .leading, spacing: 4) {
                                    Text(row.playerName)
                                        .font(.subheadline.weight(.semibold))
                                    Text("#\(row.playerNumber)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity, minHeight: 52, alignment: .leading)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 6)
                                .background(Color(uiColor: .tertiarySystemFill), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                                .overlay(alignment: .topTrailing) {
                                    Button {
                                        onPlayerEditTap(row.battingOrder)
                                    } label: {
                                        Image(systemName: "pencil")
                                            .font(.caption.weight(.semibold))
                                            .padding(6)
                                    }
                                    .buttonStyle(.plain)
                                }
                            }
                            .buttonStyle(.plain)

                            Button {
                                onPositionTap(row.battingOrder)
                            } label: {
                                Text(row.position)
                                    .font(.subheadline.weight(.semibold))
                                    .frame(maxWidth: .infinity, minHeight: 52)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 6)
                                    .background(Color(uiColor: .tertiarySystemFill), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                                    .overlay(alignment: .topTrailing) {
                                        Button {
                                            onPositionEditTap(row.battingOrder)
                                        } label: {
                                            Image(systemName: "pencil")
                                                .font(.caption.weight(.semibold))
                                                .padding(6)
                                        }
                                        .buttonStyle(.plain)
                                    }
                            }
                            .buttonStyle(.plain)
                            ForEach(Array(row.cells.enumerated()), id: \.offset) { index, cell in
                                let inning = teamCard.innings[index]
                                Button {
                                    onCellTap(
                                        ScorecardCellTapInfo(
                                            half: half,
                                            inning: inning,
                                            battingOrder: row.battingOrder,
                                            cell: cell
                                        )
                                    )
                                } label: {
                                    if let cell {
                                        ScorecardCellView(cell: cell)
                                    } else {
                                        ScorecardEmptyCellView()
                                    }
                                }
                                .buttonStyle(.plain)
                                .contentShape(RoundedRectangle(cornerRadius: 16, style: .continuous))
                                .frame(width: 84, height: 84)
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

private struct ScorecardCellTapInfo: Identifiable {
    let half: HalfCode
    let inning: Int
    let battingOrder: Int
    let cell: ScorecardCell?

    var id: String {
        "\(half.rawValue)-\(inning)-\(battingOrder)-\(cell?.id ?? "empty")"
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

private struct ScorecardEmptyCellView: View {
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 16, style: .continuous)
                .stroke(Color.secondary.opacity(0.25), style: StrokeStyle(lineWidth: 1, dash: [3, 3]))

            GeometryReader { proxy in
                let width = proxy.size.width
                let height = proxy.size.height
                let top = CGPoint(x: width / 2, y: 12)
                let left = CGPoint(x: 12, y: height / 2)
                let right = CGPoint(x: width - 12, y: height / 2)
                let bottom = CGPoint(x: width / 2, y: height - 12)

                Path { path in
                    path.move(to: top)
                    path.addLine(to: right)
                    path.addLine(to: bottom)
                    path.addLine(to: left)
                    path.closeSubpath()
                }
                .stroke(Color.secondary.opacity(0.25), lineWidth: 1)
            }
            .padding(10)
        }
    }
}

private struct DiamondBasePicker: View {
    let selectedBase: BaseCode?
    let onSelect: (BaseCode) -> Void

    var body: some View {
        GeometryReader { proxy in
            let size = min(proxy.size.width, proxy.size.height)
            let mid = CGPoint(x: size / 2, y: size / 2)
            let inset: CGFloat = 24
            let top = CGPoint(x: mid.x, y: inset)
            let right = CGPoint(x: size - inset, y: mid.y)
            let bottom = CGPoint(x: mid.x, y: size - inset)
            let left = CGPoint(x: inset, y: mid.y)

            ZStack {
                Path { path in
                    path.move(to: top)
                    path.addLine(to: right)
                    path.addLine(to: bottom)
                    path.addLine(to: left)
                    path.closeSubpath()
                }
                .stroke(Color.secondary.opacity(0.25), lineWidth: 2)

                DiamondBaseButton(title: "2B", isSelected: selectedBase == .second) {
                    onSelect(.second)
                }
                .position(top)

                DiamondBaseButton(title: "1B", isSelected: selectedBase == .first) {
                    onSelect(.first)
                }
                .position(right)

                DiamondBaseButton(title: "3B", isSelected: selectedBase == .third) {
                    onSelect(.third)
                }
                .position(left)

                DiamondBaseButton(title: "Home", isSelected: selectedBase == .home) {
                    onSelect(.home)
                }
                .position(bottom)

                DiamondBaseButton(title: "Out", isSelected: selectedBase == .out) {
                    onSelect(.out)
                }
                .position(mid)
            }
            .frame(width: size, height: size)
        }
        .aspectRatio(1, contentMode: .fit)
    }
}

private struct DiamondBaseButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.primary)
                .frame(width: 52, height: 34)
        }
        .buttonStyle(.plain)
        .background(
            Capsule()
                .fill(isSelected ? Color.accentColor.opacity(0.22) : Color(uiColor: .secondarySystemBackground))
        )
        .overlay(
            Capsule()
                .stroke(isSelected ? Color.accentColor : Color.secondary.opacity(0.2), lineWidth: 1)
        )
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

private struct DefenseDiamondView: View {
    let title: String
    let rows: [DefenseRow]

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)

            GeometryReader { proxy in
                let size = min(proxy.size.width, proxy.size.height)
                let mid = CGPoint(x: size / 2, y: size / 2)
                let inset: CGFloat = 24
                let top = CGPoint(x: mid.x, y: inset)
                let right = CGPoint(x: size - inset, y: mid.y)
                let bottom = CGPoint(x: mid.x, y: size - inset)
                let left = CGPoint(x: inset, y: mid.y)
                let shallowLeft = CGPoint(x: inset + 10, y: mid.y - 56)
                let shallowRight = CGPoint(x: size - inset - 10, y: mid.y - 56)
                let deepLeft = CGPoint(x: inset, y: inset + 16)
                let deepRight = CGPoint(x: size - inset, y: inset + 16)
                let centerField = CGPoint(x: mid.x, y: inset)

                ZStack {
                    Path { path in
                        path.move(to: bottom)
                        path.addLine(to: right)
                        path.addLine(to: top)
                        path.addLine(to: left)
                        path.closeSubpath()
                    }
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 2)

                    DefenseTag(text: playerLastName(.c)).position(bottom)
                    DefenseTag(text: playerLastName(.p)).position(mid)
                    DefenseTag(text: playerLastName(.firstBase)).position(right)
                    DefenseTag(text: playerLastName(.secondBase)).position(shallowRight)
                    DefenseTag(text: playerLastName(.ss)).position(shallowLeft)
                    DefenseTag(text: playerLastName(.thirdBase)).position(left)
                    DefenseTag(text: playerLastName(.lf)).position(deepLeft)
                    DefenseTag(text: playerLastName(.cf)).position(centerField)
                    DefenseTag(text: playerLastName(.rf)).position(deepRight)
                }
                .frame(width: size, height: size)
            }
            .aspectRatio(1, contentMode: .fit)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(18)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private func playerLastName(_ position: Position) -> String {
        guard let row = rows.first(where: { $0.position == position.display }) else { return "—" }
        return row.playerName.split(separator: " ").last.map(String.init) ?? row.playerName
    }
}

private struct DefenseTag: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.caption.weight(.semibold))
            .lineLimit(1)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Color(uiColor: .secondarySystemBackground), in: Capsule())
            .overlay(
                Capsule()
                    .stroke(Color.secondary.opacity(0.2), lineWidth: 1)
            )
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
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    SheetSection(title: "Batter") {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("#\(draft.battingOrder) \(draft.batterName)")
                                .font(.title3.weight(.semibold))
                            Text("Inning \(draft.inning) \(draft.half.shortLabel)")
                                .foregroundStyle(.secondary)
                        }
                    }

                    SheetSection(title: "Tap Base For Hit") {
                        DiamondBasePicker(selectedBase: draft.batterDestination ?? draft.resultType.batterDefaultBase) { base in
                            applyHitBaseSelection(base)
                        }
                        .frame(maxWidth: 220)
                    }

                    SheetSection(title: "Result") {
                        let columns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
                        LazyVGrid(columns: columns, spacing: 10) {
                            ForEach(ResultType.allCases) { resultType in
                                SelectionButton(
                                    title: resultType.display,
                                    isSelected: draft.resultType == resultType
                                ) {
                                    draft.resultType = resultType
                                    draft = refreshAtBatDraft(draft, state: snapshotState, battingTeam: battingTeam)
                                }
                            }
                        }
                    }

                    SheetSection(title: "Outcome") {
                        VStack(alignment: .leading, spacing: 12) {
                            Text("Outs on play")
                                .font(.subheadline.weight(.semibold))
                            let outsColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 4)
                            LazyVGrid(columns: outsColumns, spacing: 10) {
                                ForEach(0...3, id: \.self) { outs in
                                    SelectionButton(title: "\(outs)", isSelected: draft.outsOnPlay == outs) {
                                        draft.outsOnPlay = outs
                                    }
                                }
                            }

                            if draft.batterReachedVisible {
                                Text("Batter reached")
                                    .font(.subheadline.weight(.semibold))
                                let reachedColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
                                LazyVGrid(columns: reachedColumns, spacing: 10) {
                                    SelectionButton(title: "Out", isSelected: !draft.batterReached) {
                                        draft.batterReached = false
                                    }
                                    SelectionButton(title: "Safe", isSelected: draft.batterReached) {
                                        draft.batterReached = true
                                    }
                                }
                            }

                            if draft.resultType.batterDefaultBase != nil || draft.batterReached {
                                Text("Batter destination")
                                    .font(.subheadline.weight(.semibold))
                                let baseColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 4)
                                LazyVGrid(columns: baseColumns, spacing: 10) {
                                    ForEach([BaseCode.first, .second, .third, .home]) { base in
                                        SelectionButton(
                                            title: base.display,
                                            isSelected: (draft.batterDestination ?? .first) == base
                                        ) {
                                            draft.batterDestination = base
                                        }
                                    }
                                }
                            }

                            Text("RBI")
                                .font(.subheadline.weight(.semibold))
                            let rbiColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 5)
                            LazyVGrid(columns: rbiColumns, spacing: 10) {
                                ForEach(0...4, id: \.self) { count in
                                    SelectionButton(title: "\(count)", isSelected: draft.rbiCount == count) {
                                        draft.rbiCount = count
                                    }
                                }
                            }
                        }
                    }

                    if !draft.runnerAdvances.isEmpty {
                        SheetSection(title: "Runner Advances") {
                            VStack(alignment: .leading, spacing: 12) {
                                ForEach($draft.runnerAdvances) { $advance in
                                    VStack(alignment: .leading, spacing: 8) {
                                        Text("\(advance.runnerName) from \(advance.fromBase.display)")
                                            .font(.subheadline.weight(.semibold))
                                        let baseColumns = Array(repeating: GridItem(.flexible(), spacing: 8), count: 5)
                                        LazyVGrid(columns: baseColumns, spacing: 8) {
                                            ForEach([BaseCode.first, .second, .third, .home, .out]) { base in
                                                SelectionButton(title: base.display, isSelected: advance.toBase == base) {
                                                    advance.toBase = base
                                                }
                                            }
                                        }
                                    }
                                    .padding(.vertical, 6)
                                }
                            }
                        }
                    }

                    SheetSection(title: "Fielders") {
                        FielderPad(fielders: $draft.fielders)
                    }

                    SheetSection(title: "Quick Notes") {
                        NoteChips(notes: $draft.notes)
                    }
                }
                .padding(24)
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

    private func applyHitBaseSelection(_ base: BaseCode) {
        let resultType: ResultType
        switch base {
        case .first:
            resultType = .single
        case .second:
            resultType = .double
        case .third:
            resultType = .triple
        case .home:
            resultType = .homeRun
        case .out:
            return
        }

        var updated = draft
        updated.resultType = resultType
        updated.batterReached = true
        updated.batterDestination = base
        updated.outsOnPlay = resultType.defaultOuts
        draft = refreshAtBatDraft(updated, state: snapshotState, battingTeam: battingTeam)
    }
}

private struct BaserunnerSheet: View {
    let onEditAtBat: (() -> Void)?
    let onSave: (BaserunnerDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: BaserunnerDraft

    init(initialDraft: BaserunnerDraft, onEditAtBat: (() -> Void)? = nil, onSave: @escaping (BaserunnerDraft) -> Void) {
        self.onEditAtBat = onEditAtBat
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    SheetSection(title: "Runner") {
                        let fromColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
                        LazyVGrid(columns: fromColumns, spacing: 10) {
                            ForEach([BaseCode.first, .second, .third]) { base in
                                SelectionButton(title: base.display, isSelected: draft.fromBase == base) {
                                    draft.fromBase = base
                                }
                            }
                        }
                    }

                    SheetSection(title: "Destination") {
                        DiamondBasePicker(selectedBase: draft.toBase) { base in
                            draft.toBase = base
                        }
                        .frame(maxWidth: 220)

                        let toColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 4)
                        LazyVGrid(columns: toColumns, spacing: 10) {
                            ForEach([BaseCode.second, .third, .home, .out]) { base in
                                SelectionButton(title: base.display, isSelected: draft.toBase == base) {
                                    draft.toBase = base
                                }
                            }
                        }
                    }

                    SheetSection(title: "Advance Type") {
                        let howColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
                        LazyVGrid(columns: howColumns, spacing: 10) {
                            ForEach(BaserunnerType.allCases) { baserunnerType in
                                SelectionButton(title: baserunnerType.rawValue, isSelected: draft.how == baserunnerType) {
                                    draft.how = baserunnerType
                                }
                            }
                        }
                    }

                    SheetSection(title: "Fielders") {
                        FielderPad(fielders: $draft.fielders)
                    }
                }
                .padding(24)
            }
            .navigationTitle("Baserunner Event")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                if let onEditAtBat {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Edit At Bat") {
                            dismiss()
                            onEditAtBat()
                        }
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
}

private struct SubstitutionSheet: View {
    let teams: (away: Team, home: Team)
    let onSave: (SubstitutionDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: SubstitutionDraft
    @State private var nameSource: SubstitutionNameSource

    init(initialDraft: SubstitutionDraft, teams: (away: Team, home: Team), onSave: @escaping (SubstitutionDraft) -> Void) {
        self.teams = teams
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
        let initialNames = (initialDraft.team == .top ? teams.away.sortedLineup : teams.home.sortedLineup).map { $0.player.name }
        let initialSource: SubstitutionNameSource = initialNames.contains(initialDraft.enteringName) ? .lineup : .bench
        _nameSource = State(initialValue: initialSource)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    SheetSection(title: "Team") {
                        let teamColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
                        LazyVGrid(columns: teamColumns, spacing: 10) {
                            SelectionButton(title: "Away", isSelected: draft.team == .top) {
                                draft.team = .top
                                syncNameForTeamChange()
                            }
                            SelectionButton(title: "Home", isSelected: draft.team == .bottom) {
                                draft.team = .bottom
                                syncNameForTeamChange()
                            }
                        }
                    }

                    SheetSection(title: "Batting Order") {
                        let orderColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
                        LazyVGrid(columns: orderColumns, spacing: 10) {
                            ForEach(1...9, id: \.self) { order in
                                SelectionButton(title: "#\(order)", isSelected: draft.battingOrder == order) {
                                    draft.battingOrder = order
                                }
                            }
                        }
                    }

                    SheetSection(title: "Entering Player") {
                        Picker("Source", selection: $nameSource) {
                            Text("Lineup").tag(SubstitutionNameSource.lineup)
                            Text("Bench #").tag(SubstitutionNameSource.bench)
                        }
                        .pickerStyle(.segmented)
                        .onChange(of: nameSource) { _, _ in
                            syncNameForTeamChange()
                        }

                        if nameSource == .lineup {
                            let names = lineupNames(for: draft.team)
                            let nameColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
                            LazyVGrid(columns: nameColumns, spacing: 10) {
                                ForEach(names, id: \.self) { name in
                                    SelectionButton(title: name, isSelected: draft.enteringName == name) {
                                        draft.enteringName = name
                                    }
                                }
                            }
                        } else {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Bench #\(draft.enteringNumber)")
                                    .font(.title3.weight(.semibold))
                                Stepper("Number", value: $draft.enteringNumber, in: 0...99)
                                    .controlSize(.large)
                                    .onChange(of: draft.enteringNumber) { _, _ in
                                        draft.enteringName = "Bench #\(draft.enteringNumber)"
                                    }
                            }
                            .onAppear {
                                draft.enteringName = "Bench #\(draft.enteringNumber)"
                            }
                        }
                    }

                    SheetSection(title: "Position") {
                        let positionColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
                        LazyVGrid(columns: positionColumns, spacing: 10) {
                            ForEach(Position.allCases) { position in
                                SelectionButton(title: position.display, isSelected: draft.newPosition == position) {
                                    draft.newPosition = position
                                }
                            }
                        }
                    }

                    SheetSection(title: "Sub Type") {
                        let typeColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
                        LazyVGrid(columns: typeColumns, spacing: 10) {
                            ForEach(SubType.allCases) { subType in
                                SelectionButton(title: subType.rawValue, isSelected: draft.subType == subType) {
                                    draft.subType = subType
                                }
                            }
                        }
                    }
                }
                .padding(24)
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

    private func lineupNames(for team: HalfCode) -> [String] {
        let lineup = team == .top ? teams.away.sortedLineup : teams.home.sortedLineup
        return lineup.map { $0.player.name }
    }

    private func syncNameForTeamChange() {
        if nameSource == .lineup {
            let names = lineupNames(for: draft.team)
            if let first = names.first {
                draft.enteringName = first
            }
        } else {
            draft.enteringName = "Bench #\(draft.enteringNumber)"
        }
    }
}

private enum SubstitutionNameSource: String, CaseIterable, Identifiable {
    case lineup
    case bench

    var id: String { rawValue }
}

private struct PlayerEditDraft: Identifiable {
    let team: HalfCode
    let battingOrder: Int
    var name: String
    var number: Int
    var position: Position

    var id: String {
        "\(team.rawValue)-\(battingOrder)-edit"
    }
}

private struct EditPlayerSheet: View {
    let onSave: (PlayerEditDraft) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var draft: PlayerEditDraft

    init(initialDraft: PlayerEditDraft, onSave: @escaping (PlayerEditDraft) -> Void) {
        self.onSave = onSave
        _draft = State(initialValue: initialDraft)
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    SheetSection(title: "Player") {
                        TextField("Player name", text: $draft.name)
                            .textFieldStyle(.roundedBorder)
                            .font(.title3)

                        Stepper("Number: \(draft.number)", value: $draft.number, in: 0...99)
                            .controlSize(.large)
                    }

                    SheetSection(title: "Position") {
                        let positionColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
                        LazyVGrid(columns: positionColumns, spacing: 10) {
                            ForEach(Position.allCases) { position in
                                SelectionButton(title: position.display, isSelected: draft.position == position) {
                                    draft.position = position
                                }
                            }
                        }
                    }
                }
                .padding(24)
            }
            .navigationTitle("Edit Player")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Save") {
                        onSave(draft)
                        dismiss()
                    }
                }
            }
        }
    }
}

private struct SheetSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(title)
                .font(.headline)
            content
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
    }
}

private struct SelectionButton: View {
    let title: String
    let isSelected: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.primary)
                .frame(maxWidth: .infinity, minHeight: 44)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .fill(isSelected ? Color.accentColor.opacity(0.22) : Color(uiColor: .secondarySystemBackground))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .stroke(isSelected ? Color.accentColor : Color.secondary.opacity(0.2), lineWidth: 1)
        )
    }
}

private struct FielderPad: View {
    @Binding var fielders: String

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(fielders.isEmpty ? "No fielders marked" : fielders)
                .font(.subheadline.monospaced())
                .foregroundStyle(fielders.isEmpty ? .secondary : .primary)

            let columns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 3)
            LazyVGrid(columns: columns, spacing: 10) {
                ForEach(1...9, id: \.self) { number in
                    SelectionButton(title: "\(number)", isSelected: false) {
                        appendFielder("\(number)")
                    }
                }
            }

            let actionColumns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
            LazyVGrid(columns: actionColumns, spacing: 10) {
                SelectionButton(title: "Undo", isSelected: false) {
                    removeLastFielder()
                }
                SelectionButton(title: "Clear", isSelected: false) {
                    fielders = ""
                }
            }
        }
    }

    private func appendFielder(_ value: String) {
        var tokens = fielderTokens()
        tokens.append(value)
        fielders = tokens.joined(separator: "-")
    }

    private func removeLastFielder() {
        var tokens = fielderTokens()
        _ = tokens.popLast()
        fielders = tokens.joined(separator: "-")
    }

    private func fielderTokens() -> [String] {
        fielders.split(separator: "-").map(String.init)
    }
}

private struct NoteChips: View {
    @Binding var notes: String

    private let options: [String] = [
        "Hard hit",
        "Error",
        "Sacrifice",
        "Bunt",
        "Fielder's choice",
        "Infield"
    ]

    var body: some View {
        let columns = Array(repeating: GridItem(.flexible(), spacing: 10), count: 2)
        LazyVGrid(columns: columns, spacing: 10) {
            ForEach(options, id: \.self) { option in
                SelectionButton(title: option, isSelected: noteSet.contains(option)) {
                    toggle(option)
                }
            }
        }
    }

    private var noteSet: Set<String> {
        Set(notes.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty })
    }

    private func toggle(_ option: String) {
        var set = noteSet
        if set.contains(option) {
            set.remove(option)
        } else {
            set.insert(option)
        }
        notes = set.sorted().joined(separator: ", ")
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
