import struct
import unittest

import dolphin_bridge
from showdown_client import (
    CompletionDetector,
    diagnostic_messages,
    format_completion,
    format_progress,
    read_snapshot_consistent,
    read_u32_be,
    resolve_progress,
    stage_name,
    validate_counters,
)


class FakeMemory:
    def __init__(self, values, sequences=None):
        self.values = values
        self.sequences = {
            address: iter(sequence)
            for address, sequence in (sequences or {}).items()
        }

    def read_bytes(self, address, size):
        if size != 4:
            raise AssertionError("test adapter only supports u32 reads")
        value = (
            next(self.sequences[address])
            if address in self.sequences
            else self.values[address]
        )
        return struct.pack(">I", value)

    def read_u8(self, address):
        return self.values.get(address, 0)

    def write_byte(self, address, value):
        self.values[address] = value & 0xFF


class ShowdownClientTests(unittest.TestCase):
    def test_resolves_live_progress_pointer_chain(self):
        session = 0x80610000
        progress = 0x81358C84
        memory = FakeMemory({0x806F5FF0: session, session + 0x184: progress})

        self.assertEqual(resolve_progress(memory), progress)

    def test_reads_big_endian_u32(self):
        self.assertEqual(
            read_u32_be(FakeMemory({0x1000: 0x12345678}), 0x1000),
            0x12345678,
        )

    def test_uses_all_miiwiki_showdown_stage_names(self):
        self.assertEqual(stage_name(0), "Bridge")
        self.assertEqual(stage_name(9), "Volcano")
        self.assertEqual(stage_name(10), "Bridge Reverse")
        self.assertEqual(stage_name(19), "Volcano Reverse")
        self.assertEqual(stage_name(20), "Unknown (20)")

    def test_reports_stable_completion_once_after_incomplete_snapshot(self):
        detector = CompletionDetector()

        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 34))
        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 35))
        self.assertEqual(
            detector.observe(0x81358C84, 0, 35, 35),
            format_completion(0, 35, 35),
        )
        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 35))

    def test_zero_total_does_not_arm_completion(self):
        detector = CompletionDetector()

        self.assertIsNone(detector.observe(0x81358C84, 0, 0, 0))
        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 35))
        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 35))

    def test_single_complete_snapshot_does_not_report(self):
        detector = CompletionDetector()

        detector.observe(0x81358C84, 0, 35, 34)
        self.assertIsNone(detector.observe(0x81358C84, 0, 35, 35))

    def test_unknown_stage_never_reports_completion(self):
        detector = CompletionDetector()

        detector.observe(0x81358C84, 20, 35, 34)
        detector.observe(0x81358C84, 20, 35, 35)
        self.assertIsNone(detector.observe(0x81358C84, 20, 35, 35))

    def test_invalid_counter_state_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_counters(35, 36)
        with self.assertRaises(ValueError):
            validate_counters(101, 0)

    def test_reused_progress_object_can_report_a_later_stage(self):
        detector = CompletionDetector()
        progress = 0x81358C84

        detector.observe(progress, 1, 35, 34)
        detector.observe(progress, 1, 35, 35)
        self.assertEqual(
            detector.observe(progress, 1, 35, 35),
            format_completion(1, 35, 35),
        )

        self.assertIsNone(detector.observe(progress, 0, 35, 0))
        detector.observe(progress, 0, 35, 35)
        self.assertEqual(
            detector.observe(progress, 0, 35, 35),
            format_completion(0, 35, 35),
        )

    def test_reset_requires_a_new_incomplete_snapshot(self):
        detector = CompletionDetector()
        progress = 0x81358C84

        detector.observe(progress, 1, 35, 34)
        detector.observe(progress, 1, 35, 35)
        detector.observe(progress, 1, 35, 35)
        detector.reset()

        self.assertIsNone(detector.observe(progress, 0, 35, 35))
        self.assertIsNone(detector.observe(progress, 0, 35, 34))
        self.assertIsNone(detector.observe(progress, 0, 35, 35))
        self.assertEqual(
            detector.observe(progress, 0, 35, 35),
            format_completion(0, 35, 35),
        )

    def test_consistent_snapshot_returns_stable_values(self):
        session = 0x80610000
        progress = 0x81358C84
        values = {
            0x806F5FF0: session,
            session + 0x184: progress,
            progress + 0x20: 35,
            progress + 0x2C: 34,
            progress + 0x3C: 0,
        }

        self.assertEqual(
            read_snapshot_consistent(FakeMemory(values)),
            (progress, 0, 35, 34),
        )

    def test_consistent_snapshot_retries_and_fails_when_unstable(self):
        session = 0x80610000
        progress = 0x81358C84
        values = {
            0x806F5FF0: session,
            session + 0x184: progress,
            progress + 0x20: 35,
            progress + 0x2C: 34,
            progress + 0x3C: 0,
        }
        memory = FakeMemory(
            values,
            {progress + 0x2C: [34, 35, 34, 35, 34, 35]},
        )

        with self.assertRaises(ValueError):
            read_snapshot_consistent(memory)

    def test_diagnostics_only_print_on_snapshot_changes(self):
        snapshot = (0x81358C84, 0, 35, 34)

        self.assertEqual(len(diagnostic_messages(snapshot, None, False)), 2)
        self.assertEqual(diagnostic_messages(snapshot, snapshot, True), [])
        self.assertEqual(
            diagnostic_messages((0x81358C84, 0, 35, 35), snapshot, True),
            [format_progress(0, 35, 35)],
        )


class DolphinBridgeItemApplierTests(unittest.TestCase):
    def test_applies_island_flyover_no_plane_crash_upgrade(self):
        memory = FakeMemory({})
        applier = dolphin_bridge.GameStateApplier(memory)

        applier._apply_no_plane_crash({"Island Flyover No Plane Crash Upgrade": 1})

        self.assertEqual(memory.read_u8(0x817FFFF1), 1)

    def test_does_not_write_no_plane_crash_mailbox_when_not_received(self):
        memory = FakeMemory({})
        applier = dolphin_bridge.GameStateApplier(memory)

        applier._apply_no_plane_crash({})

        self.assertEqual(memory.read_u8(0x817FFFF1), 0)


if __name__ == "__main__":
    unittest.main()