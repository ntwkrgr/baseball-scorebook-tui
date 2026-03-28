import Foundation

enum Position: String, CaseIterable, Codable, Hashable, Identifiable {
    case p = "1"
    case c = "2"
    case firstBase = "3"
    case secondBase = "4"
    case thirdBase = "5"
    case ss = "6"
    case lf = "7"
    case cf = "8"
    case rf = "9"
    case dh = "10"

    var id: String { rawValue }

    var display: String {
        switch self {
        case .p: return "P"
        case .c: return "C"
        case .firstBase: return "1B"
        case .secondBase: return "2B"
        case .thirdBase: return "3B"
        case .ss: return "SS"
        case .lf: return "LF"
        case .cf: return "CF"
        case .rf: return "RF"
        case .dh: return "DH"
        }
    }
}

enum BaseCode: String, CaseIterable, Codable, Hashable, Identifiable {
    case home = "HOME"
    case first = "FIRST"
    case second = "SECOND"
    case third = "THIRD"
    case out = "OUT"

    var id: String { rawValue }

    var display: String {
        switch self {
        case .home: return "Home"
        case .first: return "1B"
        case .second: return "2B"
        case .third: return "3B"
        case .out: return "Out"
        }
    }
}

enum HalfCode: String, CaseIterable, Codable, Hashable, Identifiable {
    case top = "TOP"
    case bottom = "BOTTOM"

    var id: String { rawValue }

    var shortLabel: String {
        switch self {
        case .top: return "TOP"
        case .bottom: return "BOT"
        }
    }

    var teamLabel: String {
        switch self {
        case .top: return "Away"
        case .bottom: return "Home"
        }
    }
}

enum ResultType: String, CaseIterable, Codable, Hashable, Identifiable {
    case single = "SINGLE"
    case double = "DOUBLE"
    case triple = "TRIPLE"
    case homeRun = "HOME_RUN"
    case walk = "WALK"
    case intentionalWalk = "INTENTIONAL_WALK"
    case hitByPitch = "HIT_BY_PITCH"
    case strikeout = "STRIKEOUT"
    case strikeoutLooking = "STRIKEOUT_LOOKING"
    case groundOut = "GROUND_OUT"
    case flyOut = "FLY_OUT"
    case foulOut = "FOUL_OUT"
    case lineOut = "LINE_OUT"
    case doublePlay = "DOUBLE_PLAY"
    case triplePlay = "TRIPLE_PLAY"
    case sacFly = "SAC_FLY"
    case sacBunt = "SAC_BUNT"
    case fieldersChoice = "FIELDERS_CHOICE"
    case reachedOnError = "REACHED_ON_ERROR"
    case catchersInterference = "CATCHERS_INTERFERENCE"

    var id: String { rawValue }

    var display: String {
        switch self {
        case .single: return "1B"
        case .double: return "2B"
        case .triple: return "3B"
        case .homeRun: return "HR"
        case .walk: return "BB"
        case .intentionalWalk: return "IBB"
        case .hitByPitch: return "HBP"
        case .strikeout: return "K"
        case .strikeoutLooking: return "Kl"
        case .groundOut: return "GB"
        case .flyOut: return "FB"
        case .foulOut: return "F"
        case .lineOut: return "L"
        case .doublePlay: return "DP"
        case .triplePlay: return "TP"
        case .sacFly: return "SF"
        case .sacBunt: return "SAC"
        case .fieldersChoice: return "FC"
        case .reachedOnError: return "E"
        case .catchersInterference: return "CI"
        }
    }

    var countsAsHit: Bool {
        switch self {
        case .single, .double, .triple, .homeRun:
            return true
        default:
            return false
        }
    }

    var countsAsOut: Bool {
        switch self {
        case .strikeout, .strikeoutLooking, .groundOut, .flyOut, .foulOut, .lineOut, .doublePlay, .triplePlay, .sacFly, .sacBunt:
            return true
        default:
            return false
        }
    }

    var defaultOuts: Int {
        switch self {
        case .triplePlay:
            return 3
        case .doublePlay:
            return 2
        default:
            return countsAsOut ? 1 : 0
        }
    }

    var batterDefaultBase: BaseCode? {
        switch self {
        case .single, .walk, .intentionalWalk, .hitByPitch, .fieldersChoice, .reachedOnError, .catchersInterference:
            return .first
        case .double:
            return .second
        case .triple:
            return .third
        case .homeRun:
            return .home
        default:
            return nil
        }
    }

    var batterReachedVisible: Bool {
        switch self {
        case .strikeout, .strikeoutLooking:
            return true
        default:
            return false
        }
    }
}

enum AdvanceType: String, CaseIterable, Codable, Hashable, Identifiable {
    case onHit = "ON_HIT"
    case onBB = "ON_BB"
    case onHBP = "ON_HBP"
    case onFC = "ON_FC"
    case onError = "ON_ERROR"
    case onSac = "ON_SAC"
    case onWP = "ON_WP"
    case onPB = "ON_PB"
    case onThrow = "ON_THROW"
    case onCI = "ON_CI"

    var id: String { rawValue }
}

enum BaserunnerType: String, CaseIterable, Codable, Hashable, Identifiable {
    case sb = "SB"
    case cs = "CS"
    case po = "PO"
    case wp = "WP"
    case pb = "PB"
    case bk = "BK"
    case obr = "OBR"

    var id: String { rawValue }
}

enum SubType: String, CaseIterable, Codable, Hashable, Identifiable {
    case pinchHit = "PINCH_HIT"
    case pinchRun = "PINCH_RUN"
    case defensive = "DEFENSIVE"
    case pitcherChange = "PITCHER_CHANGE"

    var id: String { rawValue }
}

enum RunnerFinalState: String, Codable, Hashable {
    case scored = "SCORED"
    case leftOnBase = "LEFT_ON_BASE"
    case out = "OUT"
    case running = "RUNNING"
}

enum SegmentState: String, Codable, Hashable {
    case dim = "DIM"
    case lit = "LIT"
    case scored = "SCORED"
}

struct Player: Codable, Hashable {
    var name: String
    var number: Int
    var position: Position
}

struct LineupSlot: Codable, Hashable, Identifiable {
    var battingOrder: Int
    var player: Player
    var position: Position
    var enteredInning: Int

    var id: Int { battingOrder }
}

struct Team: Codable, Hashable {
    var name: String
    var lineup: [LineupSlot]

    var sortedLineup: [LineupSlot] {
        lineup.sorted { $0.battingOrder < $1.battingOrder }
    }
}

struct BaseEvent: Codable, Hashable {
    var fromBase: BaseCode
    var toBase: BaseCode
    var how: AdvanceType
    var earned: Bool
    var rbi: Bool
}

private func makeEventID() -> String {
    UUID().uuidString
}

private func makeTimestamp() -> String {
    ISO8601DateFormatter().string(from: Date())
}

struct AtBatEvent: Hashable {
    var eventID: String
    var timestamp: String
    var inning: Int
    var half: HalfCode
    var battingOrder: Int
    var resultType: ResultType
    var fielders: String
    var batterReached: Bool
    var outsOnPlay: Int
    var basesReached: [BaseEvent]
    var rbiCount: Int
    var notes: String

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        inning: Int = 1,
        half: HalfCode = .top,
        battingOrder: Int = 1,
        resultType: ResultType = .groundOut,
        fielders: String = "",
        batterReached: Bool = false,
        outsOnPlay: Int = 1,
        basesReached: [BaseEvent] = [],
        rbiCount: Int = 0,
        notes: String = ""
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.inning = inning
        self.half = half
        self.battingOrder = battingOrder
        self.resultType = resultType
        self.fielders = fielders
        self.batterReached = batterReached
        self.outsOnPlay = outsOnPlay
        self.basesReached = basesReached
        self.rbiCount = rbiCount
        self.notes = notes
    }
}

struct RunnerAdvanceEvent: Hashable {
    var eventID: String
    var timestamp: String
    var inning: Int
    var half: HalfCode
    var runnerBattingOrder: Int
    var runnerAtBatInning: Int
    var fromBase: BaseCode
    var toBase: BaseCode
    var how: AdvanceType
    var earned: Bool
    var rbiBatterOrder: Int?

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        inning: Int = 1,
        half: HalfCode = .top,
        runnerBattingOrder: Int = 1,
        runnerAtBatInning: Int = 1,
        fromBase: BaseCode = .first,
        toBase: BaseCode = .second,
        how: AdvanceType = .onHit,
        earned: Bool = true,
        rbiBatterOrder: Int? = nil
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.inning = inning
        self.half = half
        self.runnerBattingOrder = runnerBattingOrder
        self.runnerAtBatInning = runnerAtBatInning
        self.fromBase = fromBase
        self.toBase = toBase
        self.how = how
        self.earned = earned
        self.rbiBatterOrder = rbiBatterOrder
    }
}

struct BaserunnerEvent: Hashable {
    var eventID: String
    var timestamp: String
    var inning: Int
    var half: HalfCode
    var runnerBattingOrder: Int
    var runnerAtBatInning: Int
    var fromBase: BaseCode
    var toBase: BaseCode
    var how: BaserunnerType
    var fielders: String
    var earned: Bool
    var outsOnPlay: Int

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        inning: Int = 1,
        half: HalfCode = .top,
        runnerBattingOrder: Int = 1,
        runnerAtBatInning: Int = 1,
        fromBase: BaseCode = .first,
        toBase: BaseCode = .second,
        how: BaserunnerType = .sb,
        fielders: String = "",
        earned: Bool = true,
        outsOnPlay: Int = 0
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.inning = inning
        self.half = half
        self.runnerBattingOrder = runnerBattingOrder
        self.runnerAtBatInning = runnerAtBatInning
        self.fromBase = fromBase
        self.toBase = toBase
        self.how = how
        self.fielders = fielders
        self.earned = earned
        self.outsOnPlay = outsOnPlay
    }
}

struct SubstitutionEvent: Hashable {
    var eventID: String
    var timestamp: String
    var inning: Int
    var half: HalfCode
    var team: HalfCode
    var battingOrder: Int
    var leavingName: String
    var enteringName: String
    var enteringNumber: Int
    var newPosition: Position
    var subType: SubType

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        inning: Int = 1,
        half: HalfCode = .top,
        team: HalfCode = .top,
        battingOrder: Int = 1,
        leavingName: String = "",
        enteringName: String = "",
        enteringNumber: Int = 0,
        newPosition: Position = .p,
        subType: SubType = .pinchHit
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.inning = inning
        self.half = half
        self.team = team
        self.battingOrder = battingOrder
        self.leavingName = leavingName
        self.enteringName = enteringName
        self.enteringNumber = enteringNumber
        self.newPosition = newPosition
        self.subType = subType
    }
}

struct ErrorEvent: Hashable {
    var eventID: String
    var timestamp: String
    var inning: Int
    var half: HalfCode
    var fielderPosition: Position
    var fielderName: String
    var notes: String

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        inning: Int = 1,
        half: HalfCode = .top,
        fielderPosition: Position = .ss,
        fielderName: String = "",
        notes: String = ""
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.inning = inning
        self.half = half
        self.fielderPosition = fielderPosition
        self.fielderName = fielderName
        self.notes = notes
    }
}

struct EditEvent: Hashable {
    var eventID: String
    var timestamp: String
    var targetEventID: String
    var correctedEvent: GameEvent
    var reason: String

    init(
        eventID: String = makeEventID(),
        timestamp: String = makeTimestamp(),
        targetEventID: String = "",
        correctedEvent: GameEvent,
        reason: String = ""
    ) {
        self.eventID = eventID
        self.timestamp = timestamp
        self.targetEventID = targetEventID
        self.correctedEvent = correctedEvent
        self.reason = reason
    }
}

indirect enum GameEvent: Hashable, Codable, Identifiable {
    case atBat(AtBatEvent)
    case runnerAdvance(RunnerAdvanceEvent)
    case baserunner(BaserunnerEvent)
    case substitution(SubstitutionEvent)
    case error(ErrorEvent)
    case edit(EditEvent)

    var id: String {
        switch self {
        case let .atBat(event): return event.eventID
        case let .runnerAdvance(event): return event.eventID
        case let .baserunner(event): return event.eventID
        case let .substitution(event): return event.eventID
        case let .error(event): return event.eventID
        case let .edit(event): return event.eventID
        }
    }

    private enum CodingKeys: String, CodingKey {
        case type
        case eventID = "event_id"
        case timestamp
        case inning
        case half
        case battingOrder = "batting_order"
        case resultType = "result_type"
        case fielders
        case batterReached = "batter_reached"
        case outsOnPlay = "outs_on_play"
        case basesReached = "bases_reached"
        case rbiCount = "rbi_count"
        case runnerBattingOrder = "runner_batting_order"
        case runnerAtBatInning = "runner_at_bat_inning"
        case fromBase = "from_base"
        case toBase = "to_base"
        case how
        case earned
        case rbiBatterOrder = "rbi_batter_order"
        case team
        case leavingName = "leaving_name"
        case enteringName = "entering_name"
        case enteringNumber = "entering_number"
        case newPosition = "new_position"
        case subType = "sub_type"
        case fielderPosition = "fielder_position"
        case fielderName = "fielder_name"
        case notes
        case targetEventID = "target_event_id"
        case correctedEvent = "corrected_event"
        case reason
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        let type = try container.decode(String.self, forKey: .type)
        let eventID = try container.decode(String.self, forKey: .eventID)
        let timestamp = try container.decode(String.self, forKey: .timestamp)

        switch type {
        case "at_bat":
            self = .atBat(
                AtBatEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    inning: try container.decode(Int.self, forKey: .inning),
                    half: try container.decode(HalfCode.self, forKey: .half),
                    battingOrder: try container.decode(Int.self, forKey: .battingOrder),
                    resultType: try container.decode(ResultType.self, forKey: .resultType),
                    fielders: try container.decode(String.self, forKey: .fielders),
                    batterReached: try container.decode(Bool.self, forKey: .batterReached),
                    outsOnPlay: try container.decode(Int.self, forKey: .outsOnPlay),
                    basesReached: try container.decode([BaseEvent].self, forKey: .basesReached),
                    rbiCount: try container.decode(Int.self, forKey: .rbiCount),
                    notes: try container.decode(String.self, forKey: .notes)
                )
            )
        case "runner_advance":
            self = .runnerAdvance(
                RunnerAdvanceEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    inning: try container.decode(Int.self, forKey: .inning),
                    half: try container.decode(HalfCode.self, forKey: .half),
                    runnerBattingOrder: try container.decode(Int.self, forKey: .runnerBattingOrder),
                    runnerAtBatInning: try container.decode(Int.self, forKey: .runnerAtBatInning),
                    fromBase: try container.decode(BaseCode.self, forKey: .fromBase),
                    toBase: try container.decode(BaseCode.self, forKey: .toBase),
                    how: try container.decode(AdvanceType.self, forKey: .how),
                    earned: try container.decode(Bool.self, forKey: .earned),
                    rbiBatterOrder: try container.decodeIfPresent(Int.self, forKey: .rbiBatterOrder)
                )
            )
        case "baserunner":
            self = .baserunner(
                BaserunnerEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    inning: try container.decode(Int.self, forKey: .inning),
                    half: try container.decode(HalfCode.self, forKey: .half),
                    runnerBattingOrder: try container.decode(Int.self, forKey: .runnerBattingOrder),
                    runnerAtBatInning: try container.decode(Int.self, forKey: .runnerAtBatInning),
                    fromBase: try container.decode(BaseCode.self, forKey: .fromBase),
                    toBase: try container.decode(BaseCode.self, forKey: .toBase),
                    how: try container.decode(BaserunnerType.self, forKey: .how),
                    fielders: try container.decode(String.self, forKey: .fielders),
                    earned: try container.decode(Bool.self, forKey: .earned),
                    outsOnPlay: try container.decode(Int.self, forKey: .outsOnPlay)
                )
            )
        case "substitution":
            self = .substitution(
                SubstitutionEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    inning: try container.decode(Int.self, forKey: .inning),
                    half: try container.decode(HalfCode.self, forKey: .half),
                    team: try container.decode(HalfCode.self, forKey: .team),
                    battingOrder: try container.decode(Int.self, forKey: .battingOrder),
                    leavingName: try container.decode(String.self, forKey: .leavingName),
                    enteringName: try container.decode(String.self, forKey: .enteringName),
                    enteringNumber: try container.decode(Int.self, forKey: .enteringNumber),
                    newPosition: try container.decode(Position.self, forKey: .newPosition),
                    subType: try container.decode(SubType.self, forKey: .subType)
                )
            )
        case "error":
            self = .error(
                ErrorEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    inning: try container.decode(Int.self, forKey: .inning),
                    half: try container.decode(HalfCode.self, forKey: .half),
                    fielderPosition: try container.decode(Position.self, forKey: .fielderPosition),
                    fielderName: try container.decode(String.self, forKey: .fielderName),
                    notes: try container.decode(String.self, forKey: .notes)
                )
            )
        case "edit":
            self = .edit(
                EditEvent(
                    eventID: eventID,
                    timestamp: timestamp,
                    targetEventID: try container.decode(String.self, forKey: .targetEventID),
                    correctedEvent: try container.decode(GameEvent.self, forKey: .correctedEvent),
                    reason: try container.decode(String.self, forKey: .reason)
                )
            )
        default:
            throw DecodingError.dataCorruptedError(forKey: .type, in: container, debugDescription: "Unknown event type \(type)")
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        switch self {
        case let .atBat(event):
            try container.encode("at_bat", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.inning, forKey: .inning)
            try container.encode(event.half, forKey: .half)
            try container.encode(event.battingOrder, forKey: .battingOrder)
            try container.encode(event.resultType, forKey: .resultType)
            try container.encode(event.fielders, forKey: .fielders)
            try container.encode(event.batterReached, forKey: .batterReached)
            try container.encode(event.outsOnPlay, forKey: .outsOnPlay)
            try container.encode(event.basesReached, forKey: .basesReached)
            try container.encode(event.rbiCount, forKey: .rbiCount)
            try container.encode(event.notes, forKey: .notes)
        case let .runnerAdvance(event):
            try container.encode("runner_advance", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.inning, forKey: .inning)
            try container.encode(event.half, forKey: .half)
            try container.encode(event.runnerBattingOrder, forKey: .runnerBattingOrder)
            try container.encode(event.runnerAtBatInning, forKey: .runnerAtBatInning)
            try container.encode(event.fromBase, forKey: .fromBase)
            try container.encode(event.toBase, forKey: .toBase)
            try container.encode(event.how, forKey: .how)
            try container.encode(event.earned, forKey: .earned)
            try container.encodeIfPresent(event.rbiBatterOrder, forKey: .rbiBatterOrder)
        case let .baserunner(event):
            try container.encode("baserunner", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.inning, forKey: .inning)
            try container.encode(event.half, forKey: .half)
            try container.encode(event.runnerBattingOrder, forKey: .runnerBattingOrder)
            try container.encode(event.runnerAtBatInning, forKey: .runnerAtBatInning)
            try container.encode(event.fromBase, forKey: .fromBase)
            try container.encode(event.toBase, forKey: .toBase)
            try container.encode(event.how, forKey: .how)
            try container.encode(event.fielders, forKey: .fielders)
            try container.encode(event.earned, forKey: .earned)
            try container.encode(event.outsOnPlay, forKey: .outsOnPlay)
        case let .substitution(event):
            try container.encode("substitution", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.inning, forKey: .inning)
            try container.encode(event.half, forKey: .half)
            try container.encode(event.team, forKey: .team)
            try container.encode(event.battingOrder, forKey: .battingOrder)
            try container.encode(event.leavingName, forKey: .leavingName)
            try container.encode(event.enteringName, forKey: .enteringName)
            try container.encode(event.enteringNumber, forKey: .enteringNumber)
            try container.encode(event.newPosition, forKey: .newPosition)
            try container.encode(event.subType, forKey: .subType)
        case let .error(event):
            try container.encode("error", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.inning, forKey: .inning)
            try container.encode(event.half, forKey: .half)
            try container.encode(event.fielderPosition, forKey: .fielderPosition)
            try container.encode(event.fielderName, forKey: .fielderName)
            try container.encode(event.notes, forKey: .notes)
        case let .edit(event):
            try container.encode("edit", forKey: .type)
            try container.encode(event.eventID, forKey: .eventID)
            try container.encode(event.timestamp, forKey: .timestamp)
            try container.encode(event.targetEventID, forKey: .targetEventID)
            try container.encode(event.correctedEvent, forKey: .correctedEvent)
            try container.encode(event.reason, forKey: .reason)
        }
    }
}

struct EventStore: Hashable {
    var events: [GameEvent] = []
    var redoStack: [GameEvent] = []

    mutating func append(_ event: GameEvent) {
        events.append(event)
        redoStack.removeAll()
    }

    @discardableResult
    mutating func undo() -> GameEvent? {
        guard let event = events.popLast() else { return nil }
        redoStack.append(event)
        return event
    }

    @discardableResult
    mutating func redo() -> GameEvent? {
        guard let event = redoStack.popLast() else { return nil }
        events.append(event)
        return event
    }

    func effectiveEvents() -> [GameEvent] {
        var corrections: [String: GameEvent] = [:]
        for event in events {
            if case let .edit(editEvent) = event {
                corrections[editEvent.targetEventID] = editEvent.correctedEvent
            }
        }

        return events.compactMap { event in
            if case .edit = event {
                return nil
            }
            return corrections[event.id] ?? event
        }
    }
}

struct RunnerInfo: Hashable {
    var battingOrder: Int
    var atBatInning: Int
}

struct InningStats: Hashable {
    var runs: Int = 0
    var hits: Int = 0
    var errors: Int = 0
    var leftOnBase: Int = 0
}

struct GameState: Hashable {
    var currentInning: Int = 1
    var currentHalf: HalfCode = .top
    var currentBatterIndex: [HalfCode: Int] = [.top: 0, .bottom: 0]
    var outs: Int = 0
    var runners: [BaseCode: RunnerInfo] = [:]
    var awayScore: Int = 0
    var homeScore: Int = 0
    var gameOver: Bool = false
    var inningStats: [InningKey: InningStats] = [:]
}

struct InningKey: Hashable {
    var inning: Int
    var half: HalfCode
}

struct ScorecardSegment: Hashable {
    var fromBase: BaseCode
    var toBase: BaseCode
    var state: SegmentState
}

struct ScorecardCell: Hashable, Identifiable {
    var id: String
    var inning: Int
    var battingOrder: Int
    var half: HalfCode
    var resultType: ResultType
    var resultDisplay: String
    var fielders: String
    var annotations: [String]
    var segments: [ScorecardSegment]
    var finalBase: BaseCode
    var finalState: RunnerFinalState
    var notes: String
}

struct ScorecardRow: Hashable, Identifiable {
    var battingOrder: Int
    var playerName: String
    var playerNumber: Int
    var position: String
    var cells: [ScorecardCell?]

    var id: Int { battingOrder }
}

struct ScorecardTeamCard: Hashable {
    var teamName: String
    var innings: [Int]
    var rows: [ScorecardRow]
}

struct DefenseRow: Hashable, Identifiable {
    var number: String
    var position: String
    var playerName: String
    var playerNumber: Int?

    var id: String { number }
}

struct ScorelineTotals: Hashable {
    var runs: Int
    var hits: Int
    var errors: Int
}

struct Scoreline: Hashable {
    var innings: [Int]
    var awayName: String
    var homeName: String
    var awayRunsByInning: [Int?]
    var homeRunsByInning: [Int?]
    var awayTotals: ScorelineTotals
    var homeTotals: ScorelineTotals
    var activeInning: Int
    var activeHalf: HalfCode
}

struct InningTotals: Hashable {
    var innings: [Int]
    var rows: [String: [Int]]
    var totals: [String: Int]
}

struct GameLogItem: Hashable, Identifiable {
    var id: String
    var text: String
}

struct TransitionScore {
    var away: Int
    var home: Int
    var awayName: String
    var homeName: String
}

struct TransitionSummary {
    var completedInning: Int
    var completedHalf: HalfCode
    var battingTeam: String
    var stats: [String: Int]
    var score: TransitionScore
}

struct GameSnapshot {
    var teams: (away: Team, home: Team)
    var state: GameState
    var scoreline: Scoreline
    var inningTotals: (away: InningTotals, home: InningTotals)
    var scorecards: (away: ScorecardTeamCard, home: ScorecardTeamCard)
    var defense: (away: [DefenseRow], home: [DefenseRow])
    var gameLog: [GameLogItem]
    var currentBatterName: String
    var gameOver: Bool
}

private let baseOrder: [BaseCode: Int] = [
    .first: 1,
    .second: 2,
    .third: 3,
    .home: 4,
    .out: 5,
]

private let baseSegments: [(BaseCode, BaseCode)] = [
    (.home, .first),
    (.first, .second),
    (.second, .third),
    (.third, .home),
]

private let defenseOrder: [Position] = [.p, .c, .firstBase, .secondBase, .thirdBase, .ss, .lf, .cf, .rf]

func deriveState(store: EventStore) -> GameState {
    var state = GameState()
    for event in store.effectiveEvents() {
        apply(event: event, to: &state)
    }
    return state
}

private func apply(event: GameEvent, to state: inout GameState) {
    switch event {
    case let .atBat(atBat):
        applyAtBat(atBat, to: &state)
    case let .runnerAdvance(runnerAdvance):
        applyRunnerAdvance(runnerAdvance, to: &state)
    case let .baserunner(baserunner):
        applyBaserunner(baserunner, to: &state)
    case .substitution:
        break
    case let .error(errorEvent):
        var stats = inningStats(for: errorEvent.inning, half: errorEvent.half, state: &state)
        stats.errors += 1
        state.inningStats[InningKey(inning: errorEvent.inning, half: errorEvent.half)] = stats
    case .edit:
        break
    }
}

private func applyAtBat(_ event: AtBatEvent, to state: inout GameState) {
    var stats = inningStats(for: event.inning, half: event.half, state: &state)
    if event.resultType.countsAsHit {
        stats.hits += 1
        state.inningStats[InningKey(inning: event.inning, half: event.half)] = stats
    }

    state.outs += event.outsOnPlay

    if event.batterReached {
        placeBatter(event, state: &state)
    }

    state.currentBatterIndex[event.half, default: 0] = (state.currentBatterIndex[event.half, default: 0] + 1) % 9
    checkHalfInningChange(state: &state)
}

private func placeBatter(_ event: AtBatEvent, state: inout GameState) {
    let finalBase: BaseCode
    if let last = event.basesReached.last {
        finalBase = last.toBase
    } else if let defaultBase = event.resultType.batterDefaultBase {
        finalBase = defaultBase
    } else {
        return
    }

    if finalBase == .home {
        scoreRun(inning: event.inning, half: event.half, state: &state)
    } else if finalBase != .out {
        state.runners[finalBase] = RunnerInfo(battingOrder: event.battingOrder, atBatInning: event.inning)
    }
}

private func applyRunnerAdvance(_ event: RunnerAdvanceEvent, to state: inout GameState) {
    state.runners.removeValue(forKey: event.fromBase)
    if event.toBase == .home {
        scoreRun(inning: event.inning, half: event.half, state: &state)
    } else if event.toBase == .out {
        state.outs += 1
        checkHalfInningChange(state: &state)
    } else {
        state.runners[event.toBase] = RunnerInfo(battingOrder: event.runnerBattingOrder, atBatInning: event.runnerAtBatInning)
    }
}

private func applyBaserunner(_ event: BaserunnerEvent, to state: inout GameState) {
    state.runners.removeValue(forKey: event.fromBase)
    if event.toBase == .home {
        scoreRun(inning: event.inning, half: event.half, state: &state)
    } else if event.toBase == .out {
        state.outs += event.outsOnPlay
        checkHalfInningChange(state: &state)
    } else {
        state.runners[event.toBase] = RunnerInfo(battingOrder: event.runnerBattingOrder, atBatInning: event.runnerAtBatInning)
    }
}

private func inningStats(for inning: Int, half: HalfCode, state: inout GameState) -> InningStats {
    let key = InningKey(inning: inning, half: half)
    if let stats = state.inningStats[key] {
        return stats
    }
    let stats = InningStats()
    state.inningStats[key] = stats
    return stats
}

private func scoreRun(inning: Int, half: HalfCode, state: inout GameState) {
    if half == .top {
        state.awayScore += 1
    } else {
        state.homeScore += 1
    }

    var stats = inningStats(for: inning, half: half, state: &state)
    stats.runs += 1
    state.inningStats[InningKey(inning: inning, half: half)] = stats
}

private func checkHalfInningChange(state: inout GameState) {
    guard state.outs >= 3 else { return }
    let key = InningKey(inning: state.currentInning, half: state.currentHalf)
    var stats = state.inningStats[key] ?? InningStats()
    stats.leftOnBase = state.runners.count
    state.inningStats[key] = stats

    state.runners.removeAll()
    state.outs = 0
    if state.currentHalf == .top {
        state.currentHalf = .bottom
    } else {
        state.currentHalf = .top
        state.currentInning += 1
    }
}

func checkGameOver(_ state: GameState) -> Bool {
    guard state.currentInning >= 9 else { return false }
    if state.currentHalf == .bottom && state.homeScore > state.awayScore {
        return true
    }
    if state.currentHalf == .top && state.currentInning >= 10 && state.homeScore != state.awayScore {
        return true
    }
    return false
}

func lookupPlayerName(battingOrder: Int, team: Team?) -> String {
    team?.sortedLineup.first(where: { $0.battingOrder == battingOrder })?.player.name ?? "#\(battingOrder)"
}

private func advanceType(for resultType: ResultType) -> AdvanceType {
    switch resultType {
    case .walk, .intentionalWalk:
        return .onBB
    case .hitByPitch:
        return .onHBP
    case .fieldersChoice:
        return .onFC
    case .reachedOnError:
        return .onError
    case .sacFly, .sacBunt:
        return .onSac
    case .catchersInterference:
        return .onCI
    default:
        return .onHit
    }
}

private func autoRunnerDestination(resultType: ResultType, from base: BaseCode) -> BaseCode {
    switch resultType {
    case .homeRun, .triple:
        return .home
    case .double:
        switch base {
        case .second, .third:
            return .home
        case .first:
            return .third
        default:
            return base
        }
    case .single:
        switch base {
        case .first: return .second
        case .second: return .third
        case .third: return .home
        default: return base
        }
    case .walk, .intentionalWalk, .hitByPitch:
        return base
    default:
        return base
    }
}

private func forcedAdvances(resultType: ResultType, runners: [BaseCode: RunnerInfo]) -> [BaseCode: BaseCode] {
    switch resultType {
    case .walk, .intentionalWalk, .hitByPitch:
        var advances: [BaseCode: BaseCode] = [:]
        if runners[.first] != nil {
            advances[.first] = .second
            if runners[.second] != nil {
                advances[.second] = .third
                if runners[.third] != nil {
                    advances[.third] = .home
                }
            }
        }
        return advances
    default:
        return [:]
    }
}

func buildBasePath(finalBase: BaseCode, how: AdvanceType, earned: Bool = true, rbi: Bool = false) -> [BaseEvent] {
    if finalBase == .out {
        return []
    }

    let limit: Int
    switch finalBase {
    case .first: limit = 1
    case .second: limit = 2
    case .third: limit = 3
    case .home: limit = 4
    case .out: limit = 0
    }

    var result: [BaseEvent] = []
    for (index, segment) in baseSegments.enumerated() where index < limit {
        result.append(
            BaseEvent(
                fromBase: segment.0,
                toBase: segment.1,
                how: how,
                earned: earned,
                rbi: rbi && segment.1 == .home
            )
        )
    }
    return result
}

func currentBatterOrder(from state: GameState) -> Int {
    state.currentBatterIndex[state.currentHalf, default: 0] + 1
}

struct RunnerAdvanceDraft: Hashable, Identifiable {
    var fromBase: BaseCode
    var toBase: BaseCode
    var runnerBattingOrder: Int
    var runnerAtBatInning: Int
    var runnerName: String

    var id: String { "\(fromBase.rawValue)-\(runnerBattingOrder)-\(runnerAtBatInning)" }
}

struct AtBatDraft: Hashable, Identifiable {
    var inning: Int
    var half: HalfCode
    var battingOrder: Int
    var batterName: String
    var resultType: ResultType
    var fielders: String
    var outsOnPlay: Int
    var batterReachedVisible: Bool
    var batterReached: Bool
    var batterDestination: BaseCode?
    var runnerAdvances: [RunnerAdvanceDraft]
    var rbiCount: Int
    var notes: String

    var id: String { "\(half.rawValue)-\(inning)-\(battingOrder)-atbat" }
}

struct BaserunnerDraft: Hashable, Identifiable {
    var fromBase: BaseCode
    var toBase: BaseCode
    var how: BaserunnerType
    var fielders: String

    var id: String { "\(fromBase.rawValue)-\(toBase.rawValue)-runner" }
}

struct SubstitutionDraft: Hashable, Identifiable {
    var team: HalfCode
    var battingOrder: Int
    var enteringName: String
    var enteringNumber: Int
    var newPosition: Position
    var subType: SubType

    var id: String { "\(team.rawValue)-\(battingOrder)-sub" }
}

func defaultAtBatDraft(state: GameState, battingTeam: Team?, resultType: ResultType = .groundOut) -> AtBatDraft {
    let battingOrder = currentBatterOrder(from: state)
    let forced = forcedAdvances(resultType: resultType, runners: state.runners)
    let advances = state.runners
        .sorted { (baseOrder[$0.key] ?? 99) < (baseOrder[$1.key] ?? 99) }
        .map { base, runnerInfo in
            RunnerAdvanceDraft(
                fromBase: base,
                toBase: forced[base] ?? autoRunnerDestination(resultType: resultType, from: base),
                runnerBattingOrder: runnerInfo.battingOrder,
                runnerAtBatInning: runnerInfo.atBatInning,
                runnerName: lookupPlayerName(battingOrder: runnerInfo.battingOrder, team: battingTeam)
            )
        }

    return AtBatDraft(
        inning: state.currentInning,
        half: state.currentHalf,
        battingOrder: battingOrder,
        batterName: lookupPlayerName(battingOrder: battingOrder, team: battingTeam),
        resultType: resultType,
        fielders: "",
        outsOnPlay: resultType.defaultOuts,
        batterReachedVisible: resultType.batterReachedVisible,
        batterReached: false,
        batterDestination: resultType.batterDefaultBase,
        runnerAdvances: advances,
        rbiCount: 0,
        notes: ""
    )
}

func refreshAtBatDraft(_ draft: AtBatDraft, state: GameState, battingTeam: Team?) -> AtBatDraft {
    var refreshed = defaultAtBatDraft(state: state, battingTeam: battingTeam, resultType: draft.resultType)
    refreshed.fielders = draft.fielders
    refreshed.outsOnPlay = draft.outsOnPlay
    refreshed.batterReached = draft.batterReached
    refreshed.batterDestination = draft.batterDestination
    refreshed.rbiCount = draft.rbiCount
    refreshed.notes = draft.notes
    refreshed.runnerAdvances = refreshed.runnerAdvances.map { suggestion in
        if let existing = draft.runnerAdvances.first(where: { $0.id == suggestion.id }) {
            return RunnerAdvanceDraft(
                fromBase: suggestion.fromBase,
                toBase: existing.toBase,
                runnerBattingOrder: suggestion.runnerBattingOrder,
                runnerAtBatInning: suggestion.runnerAtBatInning,
                runnerName: suggestion.runnerName
            )
        }
        return suggestion
    }
    return refreshed
}

func createAtBatEvents(from draft: AtBatDraft, state: GameState) -> [GameEvent] {
    let batterOrder = currentBatterOrder(from: state)
    let reachesByDefault = draft.resultType.batterDefaultBase != nil
    let batterActuallyReaches = reachesByDefault || draft.batterReached
    let effectiveOuts = (draft.resultType == .strikeout || draft.resultType == .strikeoutLooking) && draft.batterReached ? 0 : draft.outsOnPlay
    let advanceHow = advanceType(for: draft.resultType)

    let basesReached: [BaseEvent]
    if batterActuallyReaches, let destination = draft.batterDestination ?? draft.resultType.batterDefaultBase {
        basesReached = buildBasePath(finalBase: destination, how: advanceHow, earned: true, rbi: draft.rbiCount > 0)
    } else {
        basesReached = []
    }

    let atBat = AtBatEvent(
        inning: state.currentInning,
        half: state.currentHalf,
        battingOrder: batterOrder,
        resultType: draft.resultType,
        fielders: draft.fielders.trimmingCharacters(in: .whitespacesAndNewlines),
        batterReached: batterActuallyReaches,
        outsOnPlay: effectiveOuts,
        basesReached: basesReached,
        rbiCount: max(draft.rbiCount, 0),
        notes: draft.notes.trimmingCharacters(in: .whitespacesAndNewlines)
    )

    let currentRunners = state.runners
    let runnerEvents: [GameEvent] = draft.runnerAdvances.compactMap { advance in
        guard let runnerInfo = currentRunners[advance.fromBase], advance.fromBase != advance.toBase else {
            return nil
        }
        return .runnerAdvance(
            RunnerAdvanceEvent(
                inning: state.currentInning,
                half: state.currentHalf,
                runnerBattingOrder: runnerInfo.battingOrder,
                runnerAtBatInning: runnerInfo.atBatInning,
                fromBase: advance.fromBase,
                toBase: advance.toBase,
                how: advanceHow,
                earned: true,
                rbiBatterOrder: advance.toBase == .home ? batterOrder : nil
            )
        )
    }

    return [.atBat(atBat)] + runnerEvents
}

func defaultBaserunnerDraft(state: GameState) -> BaserunnerDraft? {
    guard let firstRunner = state.runners.keys.sorted(by: { (baseOrder[$0] ?? 99) < (baseOrder[$1] ?? 99) }).first else {
        return nil
    }

    let defaultDestination: BaseCode
    switch firstRunner {
    case .first: defaultDestination = .second
    case .second: defaultDestination = .third
    case .third: defaultDestination = .home
    case .home, .out: defaultDestination = .out
    }

    return BaserunnerDraft(fromBase: firstRunner, toBase: defaultDestination, how: .sb, fielders: "")
}

func createBaserunnerEvent(from draft: BaserunnerDraft, state: GameState) -> GameEvent? {
    guard let runnerInfo = state.runners[draft.fromBase] else { return nil }
    return .baserunner(
        BaserunnerEvent(
            inning: state.currentInning,
            half: state.currentHalf,
            runnerBattingOrder: runnerInfo.battingOrder,
            runnerAtBatInning: runnerInfo.atBatInning,
            fromBase: draft.fromBase,
            toBase: draft.toBase,
            how: draft.how,
            fielders: draft.fielders.trimmingCharacters(in: .whitespacesAndNewlines),
            earned: true,
            outsOnPlay: draft.toBase == .out ? 1 : 0
        )
    )
}

func defaultSubstitutionDraft(state: GameState, awayTeam: Team, homeTeam: Team) -> SubstitutionDraft {
    let team = state.currentHalf
    return SubstitutionDraft(
        team: team,
        battingOrder: currentBatterOrder(from: state),
        enteringName: "",
        enteringNumber: 0,
        newPosition: team == .top ? awayTeam.sortedLineup.first?.position ?? .dh : homeTeam.sortedLineup.first?.position ?? .dh,
        subType: .defensive
    )
}

func createSubstitutionEvent(from draft: SubstitutionDraft, state: GameState, awayTeam: Team, homeTeam: Team) -> GameEvent {
    let sourceTeam = draft.team == .top ? awayTeam : homeTeam
    let leavingName = lookupPlayerName(battingOrder: draft.battingOrder, team: sourceTeam)
    return .substitution(
        SubstitutionEvent(
            inning: state.currentInning,
            half: state.currentHalf,
            team: draft.team,
            battingOrder: draft.battingOrder,
            leavingName: leavingName,
            enteringName: draft.enteringName.trimmingCharacters(in: .whitespacesAndNewlines),
            enteringNumber: draft.enteringNumber,
            newPosition: draft.newPosition,
            subType: draft.subType
        )
    )
}

func buildTransitionSummary(state: GameState, awayName: String, homeName: String, completedInning: Int, completedHalf: HalfCode) -> TransitionSummary {
    let key = InningKey(inning: completedInning, half: completedHalf)
    let stats = state.inningStats[key] ?? InningStats()
    return TransitionSummary(
        completedInning: completedInning,
        completedHalf: completedHalf,
        battingTeam: completedHalf == .top ? awayName : homeName,
        stats: [
            "R": stats.runs,
            "H": stats.hits,
            "E": stats.errors,
            "LOB": stats.leftOnBase,
        ],
        score: TransitionScore(away: state.awayScore, home: state.homeScore, awayName: awayName, homeName: homeName)
    )
}

func applySubstitutions(awayTeam: Team, homeTeam: Team, events: [GameEvent]) -> (away: Team, home: Team) {
    var awaySlots = awayTeam.sortedLineup
    var homeSlots = homeTeam.sortedLineup

    for event in events {
        guard case let .substitution(substitutionEvent) = event else { continue }
        var target = substitutionEvent.team == .top ? awaySlots : homeSlots
        if let index = target.firstIndex(where: { $0.battingOrder == substitutionEvent.battingOrder }) {
            target[index] = LineupSlot(
                battingOrder: substitutionEvent.battingOrder,
                player: Player(
                    name: substitutionEvent.enteringName,
                    number: substitutionEvent.enteringNumber,
                    position: substitutionEvent.newPosition
                ),
                position: substitutionEvent.newPosition,
                enteredInning: substitutionEvent.inning
            )
        }
        if substitutionEvent.team == .top {
            awaySlots = target
        } else {
            homeSlots = target
        }
    }

    return (
        away: Team(name: awayTeam.name, lineup: awaySlots.sorted { $0.battingOrder < $1.battingOrder }),
        home: Team(name: homeTeam.name, lineup: homeSlots.sorted { $0.battingOrder < $1.battingOrder })
    )
}

private func gameLogText(for event: GameEvent) -> String? {
    switch event {
    case let .atBat(atBat):
        let fielders = atBat.fielders.isEmpty ? "" : " \(atBat.fielders)"
        let rbi = atBat.rbiCount > 0 ? "  \(atBat.rbiCount) RBI" : ""
        let notes = atBat.notes.isEmpty ? "" : "  [\(atBat.notes)]"
        return "\(atBat.inning) \(atBat.half.shortLabel)  #\(atBat.battingOrder)\(fielders) \(atBat.resultType.display)\(rbi)\(notes)"
    case let .runnerAdvance(runnerAdvance):
        return "\(runnerAdvance.inning) \(runnerAdvance.half.shortLabel)  Runner #\(runnerAdvance.runnerBattingOrder): \(runnerAdvance.fromBase.rawValue)→\(runnerAdvance.toBase.rawValue)"
    case let .baserunner(baserunner):
        let fielders = baserunner.fielders.isEmpty ? "" : " (\(baserunner.fielders))"
        return "\(baserunner.inning) \(baserunner.half.shortLabel)  #\(baserunner.runnerBattingOrder) \(baserunner.how.rawValue)\(fielders): \(baserunner.fromBase.rawValue)→\(baserunner.toBase.rawValue)"
    case let .substitution(substitution):
        return "\(substitution.inning) \(substitution.half.shortLabel)  SUB (\(substitution.subType.rawValue)): #\(substitution.enteringNumber) \(substitution.enteringName) for \(substitution.leavingName)"
    case .error, .edit:
        return nil
    }
}

private func baseSequence(to finalBase: BaseCode) -> [(BaseCode, BaseCode)] {
    switch finalBase {
    case .first:
        return [(.home, .first)]
    case .second:
        return [(.home, .first), (.first, .second)]
    case .third:
        return [(.home, .first), (.first, .second), (.second, .third)]
    case .home:
        return [(.home, .first), (.first, .second), (.second, .third), (.third, .home)]
    case .out:
        return []
    }
}

private func makeCell(for event: AtBatEvent) -> ScorecardCell {
    let finalBase: BaseCode
    let finalState: RunnerFinalState
    if event.batterReached {
        finalBase = event.basesReached.last?.toBase ?? event.resultType.batterDefaultBase ?? .first
        finalState = finalBase == .home ? .scored : .running
    } else {
        finalBase = .home
        finalState = .out
    }

    let segments: [ScorecardSegment]
    if !event.basesReached.isEmpty {
        segments = event.basesReached.map {
            ScorecardSegment(
                fromBase: $0.fromBase,
                toBase: $0.toBase,
                state: $0.toBase == .home ? .scored : .lit
            )
        }
    } else if event.batterReached {
        segments = baseSequence(to: finalBase).map {
            ScorecardSegment(fromBase: $0.0, toBase: $0.1, state: $0.1 == .home ? .scored : .lit)
        }
    } else {
        segments = []
    }

    return ScorecardCell(
        id: "\(event.half.rawValue)-\(event.battingOrder)-\(event.inning)",
        inning: event.inning,
        battingOrder: event.battingOrder,
        half: event.half,
        resultType: event.resultType,
        resultDisplay: event.resultType.display,
        fielders: event.fielders,
        annotations: [],
        segments: segments,
        finalBase: finalBase,
        finalState: finalState,
        notes: event.notes
    )
}

private func updateFinal(cell: inout ScorecardCell, to base: BaseCode, outFromBase: BaseCode? = nil) {
    switch base {
    case .home:
        cell.finalBase = .home
        cell.finalState = .scored
    case .out:
        cell.finalBase = outFromBase ?? .home
        cell.finalState = .out
    default:
        cell.finalBase = base
        cell.finalState = .running
    }
}

private func markLeftOnBase(activeRunners: [BaseCode: (HalfCode, Int, Int)], cells: inout [String: ScorecardCell]) {
    for (base, key) in activeRunners {
        let lookup = "\(key.0.rawValue)-\(key.1)-\(key.2)"
        guard var cell = cells[lookup] else { continue }
        cell.finalBase = base
        cell.finalState = .leftOnBase
        cells[lookup] = cell
    }
}

private func buildScorecards(awayTeam: Team, homeTeam: Team, events: [GameEvent]) -> (away: ScorecardTeamCard, home: ScorecardTeamCard) {
    var cells: [String: ScorecardCell] = [:]
    var activeRunners: [BaseCode: (HalfCode, Int, Int)] = [:]
    var outs = 0

    for event in events {
        switch event {
        case let .atBat(atBat):
            let key = "\(atBat.half.rawValue)-\(atBat.battingOrder)-\(atBat.inning)"
            let cell = makeCell(for: atBat)
            cells[key] = cell
            if atBat.batterReached, cell.finalBase != .home, cell.finalBase != .out {
                activeRunners[cell.finalBase] = (atBat.half, atBat.battingOrder, atBat.inning)
            }
            outs += atBat.outsOnPlay
            if outs >= 3 {
                markLeftOnBase(activeRunners: activeRunners, cells: &cells)
                activeRunners.removeAll()
                outs = 0
            }
        case let .runnerAdvance(runnerAdvance):
            let runnerKey = activeRunners.removeValue(forKey: runnerAdvance.fromBase) ?? (runnerAdvance.half, runnerAdvance.runnerBattingOrder, runnerAdvance.runnerAtBatInning)
            let key = "\(runnerKey.0.rawValue)-\(runnerKey.1)-\(runnerKey.2)"
            guard var cell = cells[key] else { continue }
            cell.segments.append(
                ScorecardSegment(
                    fromBase: runnerAdvance.fromBase,
                    toBase: runnerAdvance.toBase,
                    state: runnerAdvance.toBase == .home ? .scored : .lit
                )
            )
            updateFinal(cell: &cell, to: runnerAdvance.toBase, outFromBase: runnerAdvance.fromBase)
            cells[key] = cell
            if runnerAdvance.toBase != .home, runnerAdvance.toBase != .out {
                activeRunners[runnerAdvance.toBase] = runnerKey
            }
            if runnerAdvance.toBase == .out {
                outs += 1
                if outs >= 3 {
                    markLeftOnBase(activeRunners: activeRunners, cells: &cells)
                    activeRunners.removeAll()
                    outs = 0
                }
            }
        case let .baserunner(baserunner):
            let runnerKey = activeRunners.removeValue(forKey: baserunner.fromBase) ?? (baserunner.half, baserunner.runnerBattingOrder, baserunner.runnerAtBatInning)
            let key = "\(runnerKey.0.rawValue)-\(runnerKey.1)-\(runnerKey.2)"
            guard var cell = cells[key] else { continue }
            cell.segments.append(
                ScorecardSegment(
                    fromBase: baserunner.fromBase,
                    toBase: baserunner.toBase,
                    state: baserunner.toBase == .home ? .scored : .lit
                )
            )
            var annotations = cell.annotations
            let label = baserunner.fielders.isEmpty ? baserunner.how.rawValue : "\(baserunner.how.rawValue) \(baserunner.fielders)"
            annotations.append(label)
            cell.annotations = Array(annotations.suffix(3))
            updateFinal(cell: &cell, to: baserunner.toBase, outFromBase: baserunner.fromBase)
            cells[key] = cell
            if baserunner.toBase != .home, baserunner.toBase != .out {
                activeRunners[baserunner.toBase] = runnerKey
            }
            if baserunner.toBase == .out {
                outs += baserunner.outsOnPlay
                if outs >= 3 {
                    markLeftOnBase(activeRunners: activeRunners, cells: &cells)
                    activeRunners.removeAll()
                    outs = 0
                }
            }
        case .substitution, .error, .edit:
            continue
        }
    }

    func buildTeamCard(team: Team, half: HalfCode) -> ScorecardTeamCard {
        let inningsSeen = cells.values.filter { $0.half == half }.map(\.inning)
        let innings = Array(1...max(max(inningsSeen.max() ?? 0, 9), 9))
        let rows = team.sortedLineup.map { slot in
            ScorecardRow(
                battingOrder: slot.battingOrder,
                playerName: slot.player.name,
                playerNumber: slot.player.number,
                position: slot.position.display,
                cells: innings.map { inning in
                    cells["\(half.rawValue)-\(slot.battingOrder)-\(inning)"]
                }
            )
        }
        return ScorecardTeamCard(teamName: team.name, innings: innings, rows: rows)
    }

    return (away: buildTeamCard(team: awayTeam, half: .top), home: buildTeamCard(team: homeTeam, half: .bottom))
}

private func buildDefense(for team: Team) -> [DefenseRow] {
    var positionMap: [Position: LineupSlot] = [:]
    for slot in team.sortedLineup {
        if let existing = positionMap[slot.position] {
            if slot.enteredInning > existing.enteredInning {
                positionMap[slot.position] = slot
            }
        } else {
            positionMap[slot.position] = slot
        }
    }

    return defenseOrder.map { position in
        let slot = positionMap[position]
        return DefenseRow(
            number: position.rawValue,
            position: position.display,
            playerName: slot?.player.name ?? "—",
            playerNumber: slot?.player.number
        )
    }
}

private func buildScoreline(state: GameState, awayName: String, homeName: String) -> Scoreline {
    let innings = state.inningStats.keys.map(\.inning)
    let inningList = Array(1...max(max(innings.max() ?? 0, 9), 9))

    func runs(for half: HalfCode) -> [Int?] {
        inningList.map { inning in
            let key = InningKey(inning: inning, half: half)
            if let stats = state.inningStats[key] {
                return stats.runs
            }
            if inning < state.currentInning {
                return 0
            }
            if inning == state.currentInning, state.currentHalf == .bottom, half == .top {
                return 0
            }
            return nil
        }
    }

    var awayHits = 0
    var awayErrors = 0
    var homeHits = 0
    var homeErrors = 0
    for (key, stats) in state.inningStats {
        if key.half == .top {
            awayHits += stats.hits
            awayErrors += stats.errors
        } else {
            homeHits += stats.hits
            homeErrors += stats.errors
        }
    }

    return Scoreline(
        innings: inningList,
        awayName: awayName,
        homeName: homeName,
        awayRunsByInning: runs(for: .top),
        homeRunsByInning: runs(for: .bottom),
        awayTotals: ScorelineTotals(runs: state.awayScore, hits: awayHits, errors: awayErrors),
        homeTotals: ScorelineTotals(runs: state.homeScore, hits: homeHits, errors: homeErrors),
        activeInning: state.currentInning,
        activeHalf: state.currentHalf
    )
}

private func buildInningTotals(state: GameState, half: HalfCode) -> InningTotals {
    let innings = state.inningStats.keys.filter { $0.half == half }.map(\.inning).sorted()
    var rows: [String: [Int]] = ["R": [], "H": [], "E": [], "LOB": []]
    var totals: [String: Int] = ["R": 0, "H": 0, "E": 0, "LOB": 0]

    for inning in innings {
        let stats = state.inningStats[InningKey(inning: inning, half: half)] ?? InningStats()
        rows["R", default: []].append(stats.runs)
        rows["H", default: []].append(stats.hits)
        rows["E", default: []].append(stats.errors)
        rows["LOB", default: []].append(stats.leftOnBase)
        totals["R", default: 0] += stats.runs
        totals["H", default: 0] += stats.hits
        totals["E", default: 0] += stats.errors
        totals["LOB", default: 0] += stats.leftOnBase
    }

    return InningTotals(innings: innings, rows: rows, totals: totals)
}

func buildSnapshot(awayTeam: Team, homeTeam: Team, store: EventStore, completed: Bool) -> GameSnapshot {
    let effectiveEvents = store.effectiveEvents()
    let state = deriveState(store: store)
    let liveTeams = applySubstitutions(awayTeam: awayTeam, homeTeam: homeTeam, events: effectiveEvents)
    let activeTeam = state.currentHalf == .top ? liveTeams.away : liveTeams.home
    let batterOrder = currentBatterOrder(from: state)
    let currentBatterName = lookupPlayerName(battingOrder: batterOrder, team: activeTeam)

    return GameSnapshot(
        teams: (away: liveTeams.away, home: liveTeams.home),
        state: state,
        scoreline: buildScoreline(state: state, awayName: liveTeams.away.name, homeName: liveTeams.home.name),
        inningTotals: (away: buildInningTotals(state: state, half: .top), home: buildInningTotals(state: state, half: .bottom)),
        scorecards: buildScorecards(awayTeam: liveTeams.away, homeTeam: liveTeams.home, events: effectiveEvents),
        defense: (away: buildDefense(for: liveTeams.away), home: buildDefense(for: liveTeams.home)),
        gameLog: effectiveEvents.compactMap { event in
            guard let text = gameLogText(for: event) else { return nil }
            return GameLogItem(id: event.id, text: text)
        },
        currentBatterName: currentBatterName,
        gameOver: completed || checkGameOver(state)
    )
}

struct SavedGameFile: Codable, Hashable {
    var version: String
    var date: String
    var stadium: String
    var away: SavedTeam
    var home: SavedTeam
    var events: [GameEvent]
    var completed: Bool
    var notes: String
}

struct SavedTeam: Codable, Hashable {
    var name: String
    var startingLineup: [SavedLineupSlot]

    private enum CodingKeys: String, CodingKey {
        case name
        case startingLineup = "starting_lineup"
    }
}

struct SavedLineupSlot: Codable, Hashable {
    var battingOrder: Int
    var name: String
    var number: Int
    var playerPosition: Position
    var position: Position
    var enteredInning: Int

    private enum CodingKeys: String, CodingKey {
        case battingOrder = "batting_order"
        case name
        case number
        case playerPosition = "player_position"
        case position
        case enteredInning = "entered_inning"
    }
}

struct LoadedGame {
    var awayTeam: Team
    var homeTeam: Team
    var store: EventStore
    var date: String
    var stadium: String
    var completed: Bool
    var notes: String
}

enum ScorebookPersistence {
    static let formatVersion = "1.0"

    static func defaultSaveDirectory() throws -> URL {
        let documents = try FileManager.default.url(for: .documentDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
        let directory = documents.appendingPathComponent("SavedGames", isDirectory: true)
        if !FileManager.default.fileExists(atPath: directory.path) {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        }
        return directory
    }

    static func generateFilename(awayName: String, homeName: String, date: String) -> String {
        let effectiveDate = date.isEmpty ? ISO8601DateFormatter().string(from: Date()).prefix(10) : Substring(date)
        let safeAway = awayName.replacingOccurrences(of: " ", with: "-")
        let safeHome = homeName.replacingOccurrences(of: " ", with: "-")
        return "\(effectiveDate)_\(safeAway)-vs-\(safeHome).json"
    }

    static func saveGame(
        url: URL,
        awayTeam: Team,
        homeTeam: Team,
        store: EventStore,
        date: String = "",
        stadium: String = "",
        completed: Bool = false,
        notes: String = ""
    ) throws {
        let payload = SavedGameFile(
            version: formatVersion,
            date: date,
            stadium: stadium,
            away: SavedTeam(name: awayTeam.name, startingLineup: awayTeam.sortedLineup.map(ScorebookPersistence.savedLineupSlot)),
            home: SavedTeam(name: homeTeam.name, startingLineup: homeTeam.sortedLineup.map(ScorebookPersistence.savedLineupSlot)),
            events: store.events,
            completed: completed,
            notes: notes
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        let data = try encoder.encode(payload)
        try data.write(to: url, options: .atomic)
    }

    static func loadGame(url: URL) throws -> LoadedGame {
        let data = try Data(contentsOf: url)
        let decoder = JSONDecoder()
        let payload = try decoder.decode(SavedGameFile.self, from: data)
        let awayTeam = Team(name: payload.away.name, lineup: payload.away.startingLineup.map(ScorebookPersistence.lineupSlot))
        let homeTeam = Team(name: payload.home.name, lineup: payload.home.startingLineup.map(ScorebookPersistence.lineupSlot))
        return LoadedGame(
            awayTeam: awayTeam,
            homeTeam: homeTeam,
            store: EventStore(events: payload.events, redoStack: []),
            date: payload.date,
            stadium: payload.stadium,
            completed: payload.completed,
            notes: payload.notes
        )
    }

    static func listSavedGames() throws -> [URL] {
        let directory = try defaultSaveDirectory()
        let files = try FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: [.contentModificationDateKey], options: [.skipsHiddenFiles])
        return files
            .filter { $0.pathExtension == "json" }
            .sorted { left, right in
                let leftDate = (try? left.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                let rightDate = (try? right.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                return leftDate > rightDate
            }
    }

    static func savedLineupSlot(from slot: LineupSlot) -> SavedLineupSlot {
        SavedLineupSlot(
            battingOrder: slot.battingOrder,
            name: slot.player.name,
            number: slot.player.number,
            playerPosition: slot.player.position,
            position: slot.position,
            enteredInning: slot.enteredInning
        )
    }

    static func lineupSlot(from slot: SavedLineupSlot) -> LineupSlot {
        LineupSlot(
            battingOrder: slot.battingOrder,
            player: Player(name: slot.name, number: slot.number, position: slot.playerPosition),
            position: slot.position,
            enteredInning: slot.enteredInning
        )
    }
}
