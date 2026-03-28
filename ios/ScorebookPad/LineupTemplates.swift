import Foundation

struct TeamDraft: Hashable {
    var name: String
    var lineup: [LineupDraftSlot]

    static func empty() -> TeamDraft {
        TeamDraft(
            name: "",
            lineup: (1...9).map { battingOrder in
                LineupDraftSlot(
                    battingOrder: battingOrder,
                    playerName: "",
                    playerNumber: "",
                    position: nil
                )
            }
        )
    }

    func makeTeam() -> Team? {
        guard !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { return nil }
        let slots = lineup.compactMap { slot -> LineupSlot? in
            guard
                let position = slot.position,
                !slot.playerName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                let number = Int(slot.playerNumber)
            else {
                return nil
            }
            return LineupSlot(
                battingOrder: slot.battingOrder,
                player: Player(
                    name: slot.playerName.trimmingCharacters(in: .whitespacesAndNewlines),
                    number: number,
                    position: position
                ),
                position: position,
                enteredInning: 1
            )
        }
        guard slots.count == 9 else { return nil }
        return Team(name: name.trimmingCharacters(in: .whitespacesAndNewlines), lineup: slots)
    }
}

struct LineupDraftSlot: Hashable, Identifiable {
    var battingOrder: Int
    var playerName: String
    var playerNumber: String
    var position: Position?

    var id: Int { battingOrder }
}

enum LineupTemplates {
    private static let positions: [Position] = [.cf, .ss, .firstBase, .dh, .rf, .thirdBase, .lf, .c, .secondBase]

    private static let awayNames = [
        "Mason Wade",
        "Luke Jarvis",
        "Tyler Boone",
        "Eli Navarro",
        "Carter Bloom",
        "Jonas Pike",
        "Reed Salazar",
        "Beau Mercer",
        "Noah Keene",
    ]

    private static let homeNames = [
        "Hudson Price",
        "Gavin Doyle",
        "Jace Morrow",
        "Micah Sloan",
        "Parker Kent",
        "Wyatt Duran",
        "Tate Holloway",
        "Logan Finch",
        "Cade Sutton",
    ]

    static func generate(side: HalfCode) -> TeamDraft {
        let teamName = side == .top ? "Roadrunners" : "Rams"
        let names = side == .top ? awayNames : homeNames
        let baseNumber = side == .top ? 11 : 31

        return TeamDraft(
            name: teamName,
            lineup: names.enumerated().map { index, name in
                LineupDraftSlot(
                    battingOrder: index + 1,
                    playerName: name,
                    playerNumber: "\(baseNumber + index)",
                    position: positions[index]
                )
            }
        )
    }
}
