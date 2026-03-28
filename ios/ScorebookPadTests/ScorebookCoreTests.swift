import XCTest
@testable import ScorebookPad

final class ScorebookCoreTests: XCTestCase {
    func testEventStoreUndoRedoMaintainsLinearHistory() {
        var store = EventStore()
        store.append(.atBat(AtBatEvent(resultType: .single, batterReached: true, outsOnPlay: 0, basesReached: buildBasePath(finalBase: .first, how: .onHit))))
        store.append(.atBat(AtBatEvent(resultType: .groundOut, batterReached: false, outsOnPlay: 1)))

        XCTAssertEqual(store.events.count, 2)

        _ = store.undo()
        XCTAssertEqual(store.events.count, 1)
        XCTAssertEqual(store.redoStack.count, 1)

        _ = store.redo()
        XCTAssertEqual(store.events.count, 2)
        XCTAssertEqual(store.redoStack.count, 0)
    }

    func testStateReplayScoresRunsAndAdvancesHalfInning() {
        var store = EventStore()
        store.append(.atBat(AtBatEvent(resultType: .homeRun, batterReached: true, outsOnPlay: 0, basesReached: buildBasePath(finalBase: .home, how: .onHit))))
        store.append(.atBat(AtBatEvent(resultType: .groundOut, batterReached: false, outsOnPlay: 1)))
        store.append(.atBat(AtBatEvent(resultType: .flyOut, batterReached: false, outsOnPlay: 1)))
        store.append(.atBat(AtBatEvent(resultType: .strikeout, batterReached: false, outsOnPlay: 1)))

        let state = deriveState(store: store)

        XCTAssertEqual(state.awayScore, 1)
        XCTAssertEqual(state.currentHalf, .bottom)
        XCTAssertEqual(state.currentInning, 1)
        XCTAssertEqual(state.outs, 0)
        XCTAssertTrue(state.runners.isEmpty)
    }

    func testSaveLoadRoundTripPreservesTeamsAndEvents() throws {
        let awayTeam = makeTeam(name: "Away")
        let homeTeam = makeTeam(name: "Home")
        let url = FileManager.default.temporaryDirectory.appendingPathComponent("scorebook-core-roundtrip.json")

        var store = EventStore()
        store.append(.atBat(AtBatEvent(resultType: .single, batterReached: true, outsOnPlay: 0, basesReached: buildBasePath(finalBase: .first, how: .onHit))))
        store.append(.baserunner(BaserunnerEvent(runnerBattingOrder: 1, runnerAtBatInning: 1, fromBase: .first, toBase: .second, how: .sb)))

        try ScorebookPersistence.saveGame(url: url, awayTeam: awayTeam, homeTeam: homeTeam, store: store, completed: false)
        let loaded = try ScorebookPersistence.loadGame(url: url)

        XCTAssertEqual(loaded.awayTeam.name, "Away")
        XCTAssertEqual(loaded.homeTeam.name, "Home")
        XCTAssertEqual(loaded.store.events.count, 2)

        guard case let .baserunner(event) = loaded.store.events[1] else {
            return XCTFail("Expected baserunner event")
        }
        XCTAssertEqual(event.toBase, .second)

        try? FileManager.default.removeItem(at: url)
    }

    private func makeTeam(name: String) -> Team {
        Team(
            name: name,
            lineup: (1...9).map { order in
                let positions: [Position] = [.cf, .ss, .firstBase, .dh, .rf, .thirdBase, .lf, .c, .secondBase]
                return LineupSlot(
                    battingOrder: order,
                    player: Player(name: "\(name) Player \(order)", number: order, position: positions[order - 1]),
                    position: positions[order - 1],
                    enteredInning: 1
                )
            }
        )
    }
}
