import unittest
from collections import Counter

from football_analytics.transform.fixtures import (
    transform_fixture_team_results,
    transform_fixtures,
)


class FixtureCorrectionsTest(unittest.TestCase):
    def test_corrected_seasons_have_complete_double_round_robin(self):
        for season, expected_manual_rows in ((2010, 10), (2013, 40)):
            fixtures = transform_fixtures(season=season)

            self.assertEqual(len(fixtures), 380)
            self.assertEqual(
                int((fixtures["FixtureID"] < 0).sum()),
                expected_manual_rows,
            )
            self.assertEqual(
                set(Counter(fixtures["RoundNumber"].astype(int)).values()),
                {10},
            )
            self.assertEqual(
                set(Counter(fixtures["HomeTeamID"].astype(int)).values()),
                {19},
            )
            self.assertEqual(
                set(Counter(fixtures["AwayTeamID"].astype(int)).values()),
                {19},
            )

    def test_team_fact_has_two_rows_for_every_fixture(self):
        for season in (2010, 2013):
            fixtures = transform_fixtures(season=season)
            team_results = transform_fixture_team_results(season=season)

            self.assertEqual(len(team_results), len(fixtures) * 2)
            self.assertEqual(
                set(Counter(team_results["FixtureID"]).values()),
                {2},
            )

    def test_known_2010_api_round_is_corrected(self):
        fixtures = transform_fixtures(season=2010).set_index("FixtureID")

        corrected = fixtures.loc[list(range(191927, 191937))]
        self.assertEqual(set(corrected["RoundNumber"].astype(int)), {1})

    def test_manual_fixtures_receive_confirmed_enrichment(self):
        fixtures = transform_fixtures(season=2010).set_index("FixtureID")
        match = fixtures.loc[-2010001]

        self.assertEqual(match["VenueName"], "Arena da Baixada")
        self.assertEqual(int(match["HalftimeHomeGoals"]), 1)
        self.assertEqual(int(match["HalftimeAwayGoals"]), 0)
        self.assertEqual(
            match["FixtureDateUTC"].isoformat(),
            "2010-12-05T19:00:00+00:00",
        )
        self.assertEqual(match["Timezone"], "UTC")
        self.assertIsNotNone(match["FixtureTimestamp"])

        night_match = transform_fixtures(season=2013).set_index(
            "FixtureID"
        ).loc[-2013001]
        self.assertEqual(str(night_match["FixtureDate"]), "2013-06-05")
        self.assertEqual(night_match["DateKey"], "20130605")
        self.assertEqual(
            night_match["FixtureDateUTC"].isoformat(),
            "2013-06-06T00:00:00+00:00",
        )


if __name__ == "__main__":
    unittest.main()
