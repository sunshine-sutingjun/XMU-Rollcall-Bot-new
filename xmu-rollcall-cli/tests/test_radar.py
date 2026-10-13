import unittest
from unittest.mock import Mock, patch

import requests

from xmu_rollcall import radar_sites, verify
from xmu_rollcall.config import normalize_rollcall_settings, set_rollcall_settings
from xmu_rollcall.rollcall_handler import handle_rollcalls


XIANGAN_CENTERS = (
    ("学武楼", 24.608310, 118.309083),
    ("坤銮楼", 24.608400, 118.308034),
    ("文轩楼", 24.608067, 118.305316),
    ("中心区5号楼", 24.607684, 118.304354),
    ("正信楼", 24.606349, 118.295652),
    ("学信楼", 24.607046, 118.295212),
    ("嘉信楼", 24.607398, 118.296236),
    ("启信楼", 24.608109, 118.295517),
    ("智信楼", 24.608340, 118.296771),
    ("睿信楼", 24.609278, 118.295673),
)


def response(status, body=None):
    result = Mock()
    result.status_code = status
    result.json.return_value = {} if body is None else body
    return result


class RadarProbeTests(unittest.TestCase):
    def test_http_200_stops_immediately(self):
        session = Mock()
        session.put.return_value = response(200)
        self.assertTrue(verify.send_radar(session, 7, "xiangan"))
        self.assertEqual(session.put.call_count, 1)
        submitted = session.put.call_args.kwargs["json"]
        self.assertEqual((submitted["latitude"], submitted["longitude"]), XIANGAN_CENTERS[0][1:])
        self.assertEqual(session.put.call_args.kwargs["timeout"], (5, 8))

    def test_out_of_range_continues(self):
        session = Mock()
        session.put.side_effect = [response(400, {"message": "out of range"}), response(200)]
        self.assertTrue(verify.send_radar(session, 7, "xiangan"))
        self.assertEqual(session.put.call_count, 2)
        second = session.put.call_args_list[1].kwargs["json"]
        self.assertEqual((second["latitude"], second["longitude"]), XIANGAN_CENTERS[1][1:])

    def test_missing_distance_does_not_raise(self):
        session = Mock()
        missed = response(400, {"distance": None})
        missed.json.side_effect = TypeError("distance")
        session.put.side_effect = [missed, response(200)]
        self.assertTrue(verify.send_radar(session, 7, "xiangan"))
        self.assertEqual(session.put.call_count, 2)

    def test_unset_campus_fails_without_request(self):
        for campus in (None, "", "both"):
            with self.subTest(campus=campus):
                session = Mock()
                with patch.object(verify, "log_and_print") as printed:
                    self.assertFalse(verify.send_radar(session, 7, campus))
                session.put.assert_not_called()
                self.assertIn("config menu (c)", printed.call_args.args[0])

    def test_retryable_status_raises(self):
        missed = requests.Response()
        missed.status_code = 503
        missed.url = "https://lnt.xmu.edu.cn/api/rollcall/7/answer"
        missed.reason = "Service Unavailable"
        session = Mock()
        session.put.return_value = missed
        with self.assertRaises(requests.HTTPError):
            verify.send_radar(session, 7, "siming")
        self.assertEqual(session.put.call_count, 1)

    def test_xiangan_centers_are_tried_before_grid_points(self):
        self.assertEqual(radar_sites.XIANGAN_BUILDINGS, XIANGAN_CENTERS)
        points = radar_sites.xiangan_probe_points()
        centers = [center[1:] for center in XIANGAN_CENTERS]
        self.assertEqual(points[:len(centers)], centers)
        self.assertGreater(len(points), len(centers))
        self.assertNotIn(points[len(centers)], centers)

        recorded = []

        def put(url, json=None, **kwargs):
            recorded.append((json["latitude"], json["longitude"]))
            self.assertEqual(kwargs["timeout"], (5, 8))
            return response(400 if len(recorded) <= len(centers) else 200)

        session = Mock()
        session.put.side_effect = put
        self.assertTrue(verify.send_radar(session, 7, "xiangan"))
        self.assertEqual(recorded[:len(centers)], centers)
        self.assertEqual(recorded[len(centers)], points[len(centers)])
        self.assertEqual(len(recorded), len(centers) + 1)

        for index, point in enumerate(points):
            for earlier in points[:index]:
                self.assertGreaterEqual(
                    radar_sites._meters_between(point[0], point[1], earlier[0], earlier[1]),
                    radar_sites.XIANGAN_DEDUPE_M - 1e-6,
                )

    def test_siming_grid_stays_inside_bbox(self):
        points = radar_sites.siming_probe_points()
        self.assertEqual(points[0], (radar_sites.SIMING_LAT_MIN, radar_sites.SIMING_LON_MIN))
        self.assertGreater(len(points), 1)
        for lat, lon in points:
            self.assertGreaterEqual(lat, radar_sites.SIMING_LAT_MIN - 1e-9)
            self.assertLessEqual(lat, radar_sites.SIMING_LAT_MAX + 1e-9)
            self.assertGreaterEqual(lon, radar_sites.SIMING_LON_MIN - 1e-9)
            self.assertLessEqual(lon, radar_sites.SIMING_LON_MAX + 1e-9)

    def test_campus_is_stored_on_rollcall_settings(self):
        account = {"rollcall_settings": {"wait_before_answer": 4}}
        set_rollcall_settings(account, {"radar_campus": "XiangAn"})
        self.assertEqual(account["rollcall_settings"]["radar_campus"], "xiangan")
        self.assertEqual(account["rollcall_settings"]["wait_before_answer"], 4)
        set_rollcall_settings(account, {"wait_before_answer": False})
        self.assertEqual(account["rollcall_settings"]["radar_campus"], "xiangan")
        self.assertIs(account["rollcall_settings"]["wait_before_answer"], False)
        self.assertNotIn(
            "radar_campus",
            normalize_rollcall_settings({"wait_before_answer": 1, "radar_campus": "both"}),
        )

    def test_handler_passes_account_campus(self):
        account = {"rollcall_settings": {"wait_before_answer": False, "radar_campus": "siming"}}
        payload = {"rollcalls": [{
            "course_title": "Course",
            "created_by_name": "Teacher",
            "department_name": "Dept",
            "is_expired": False,
            "is_number": False,
            "is_radar": True,
            "rollcall_id": 99,
            "rollcall_status": "absent",
            "scored": False,
            "status": "absent",
        }]}
        with patch("xmu_rollcall.rollcall_handler.send_radar", return_value=True) as radar, patch(
            "xmu_rollcall.rollcall_handler.log_and_print"
        ):
            handle_rollcalls(payload, Mock(), account)
        radar.assert_called_once_with(unittest.mock.ANY, 99, "siming")
