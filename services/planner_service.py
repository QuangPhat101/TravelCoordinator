from models.trip_plan import TripPlan
from services.sample_data_service import SampleDataService


class PlannerService:
    def __init__(self, sample_data_service: SampleDataService) -> None:
        self.sample_data_service = sample_data_service

    def build_plan(self, start: str, end: str, preference: str) -> TripPlan:
        attractions = self.sample_data_service.load_attractions()
        transport_options = self.sample_data_service.load_transport_options()
        preference_key = preference.strip().lower()

        if attractions.empty:
            return TripPlan(
                title=f"Lộ trình từ {start} đến {end}",
                start=start,
                end=end,
                preference=preference,
                stops=["Dữ liệu mẫu chưa sẵn sàng."],
                estimated_duration_minutes=45,
                estimated_co2_saved_kg=1.8,
            )

        start_row = self._find_attraction(attractions, start)
        end_row = self._find_attraction(attractions, end, fallback_index=1)

        direct_options = transport_options.loc[
            (transport_options["origin_id"] == start_row["attraction_id"])
            & (transport_options["destination_id"] == end_row["attraction_id"])
        ].copy()

        if direct_options.empty:
            direct_options = transport_options.loc[
                (transport_options["origin_id"] == end_row["attraction_id"])
                & (transport_options["destination_id"] == start_row["attraction_id"])
            ].copy()

        if not direct_options.empty:
            if "co2" in preference_key:
                selected_option = direct_options.sort_values(
                    by=["estimated_carbon_g", "duration_min"],
                    ascending=[True, True],
                ).iloc[0]
            elif "đông" in preference_key:
                selected_option = direct_options.sort_values(
                    by=["duration_min", "estimated_carbon_g"],
                    ascending=[True, True],
                ).iloc[0]
            else:
                selected_option = direct_options.sort_values(
                    by=["duration_min", "estimated_carbon_g"],
                    ascending=[True, True],
                ).iloc[0]
        else:
            selected_option = {
                "transport_mode": "xe bus",
                "distance_km": 6.5,
                "duration_min": 22,
                "estimated_carbon_g": 180,
            }

        scenic_candidates = attractions.loc[
            ~attractions["attraction_id"].isin([start_row["attraction_id"], end_row["attraction_id"]])
        ].copy()

        if "co2" in preference_key:
            scenic_candidates = scenic_candidates.sort_values(
                by=["indoor_outdoor", "popularity_score", "avg_rating"],
                ascending=[False, True, False],
            )
        elif "đông" in preference_key:
            scenic_candidates = scenic_candidates.sort_values(
                by=["popularity_score", "avg_rating"],
                ascending=[True, False],
            )
        else:
            scenic_candidates = scenic_candidates.sort_values(
                by=["popularity_score", "avg_rating"],
                ascending=[False, False],
            )

        stop_names = scenic_candidates.head(2)["name"].tolist()
        stops = [
            f'Xuất phát tại {start_row["name"]}.',
            f'Ưu tiên di chuyển bằng {selected_option["transport_mode"]}.',
            f'Quãng đường khoảng {float(selected_option["distance_km"]):.1f} km, thời gian {int(selected_option["duration_min"])} phút.',
        ]
        stops.extend(f"Gợi ý ghé thêm: {name}." for name in stop_names)
        stops.append(f'Kết thúc tại {end_row["name"]}.')

        baseline_carbon_g = max(float(selected_option["distance_km"]) * 210.0, 250.0)
        co2_saved = max(0.5, (baseline_carbon_g - float(selected_option["estimated_carbon_g"])) / 1000.0)

        return TripPlan(
            title=f'Lộ trình từ {start_row["name"]} đến {end_row["name"]}',
            start=str(start_row["name"]),
            end=str(end_row["name"]),
            preference=preference,
            stops=stops,
            estimated_duration_minutes=int(selected_option["duration_min"]),
            estimated_co2_saved_kg=co2_saved,
        )

    @staticmethod
    def _find_attraction(attractions, keyword: str, fallback_index: int = 0):
        normalized = keyword.strip().casefold()
        if normalized:
            exact = attractions.loc[attractions["name"].str.casefold() == normalized]
            if not exact.empty:
                return exact.iloc[0]

            partial = attractions.loc[attractions["name"].str.casefold().str.contains(normalized, regex=False)]
            if not partial.empty:
                return partial.iloc[0]

        safe_index = min(max(fallback_index, 0), len(attractions) - 1)
        return attractions.iloc[safe_index]
