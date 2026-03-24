from __future__ import annotations

from typing import Any

from config import settings
from services.crowd_forecast_service import CrowdForecastService
from services.data_loader import DataLoader
from services.eco_reward_service import EcoRewardService
from services.hidden_gem_service import HiddenGemService
from services.intent_router import IntentRouter
from services.retrieval_service import RetrievalService


class ChatbotService:
    def __init__(
        self,
        data_loader: DataLoader,
        crowd_forecast_service: CrowdForecastService | None = None,
        hidden_gem_service: HiddenGemService | None = None,
        eco_reward_service: EcoRewardService | None = None,
        intent_router: IntentRouter | None = None,
        retrieval_service: RetrievalService | None = None,
    ) -> None:
        self.data_loader = data_loader
        self.crowd_forecast_service = crowd_forecast_service
        self.hidden_gem_service = hidden_gem_service
        self.eco_reward_service = eco_reward_service
        self.intent_router = intent_router or IntentRouter()
        self.retrieval_service = retrieval_service or RetrievalService(
            data_loader=data_loader,
            crowd_forecast_service=crowd_forecast_service,
            hidden_gem_service=hidden_gem_service,
            eco_reward_service=eco_reward_service,
        )
        self.last_planner_result: dict[str, Any] | None = None

    def build_welcome_message(self) -> str:
        return (
            "Xin chào, mình là chatbot hybrid bản 1 của Eco-Travel Coordinator. "
            "Mình chạy hoàn toàn offline và đọc dữ liệu local từ dashboard, hidden gem, planner và eco reward.\n\n"
            "Bạn có thể hỏi như:\n"
            "- Điểm nào gần mà ít đông?\n"
            "- Nên đi Bảo tàng Đà Nẵng lúc mấy giờ?\n"
            "- Hidden gem nào phù hợp gần Cầu Rồng?\n"
            "- Vì sao route này được chọn?\n"
            "- Làm sao để tích điểm xanh?\n"
            "- Địa điểm nào đang đông?"
        )

    def set_last_planner_result(self, route_result: dict[str, Any] | None) -> None:
        self.last_planner_result = route_result

    def respond(self, message: str) -> str:
        intent = self.intent_router.detect_intent(message)

        if intent == "empty":
            return "Bạn cứ nhập câu hỏi ngắn về crowd, hidden gem, planner hoặc eco reward, mình sẽ hỗ trợ ngay."
        if intent == "greeting":
            return self.build_welcome_message()
        if intent == "nearby_low_crowd":
            return self._answer_nearby_low_crowd(message)
        if intent == "best_visit_time":
            return self._answer_best_visit_time(message)
        if intent == "hidden_gem_match":
            return self._answer_hidden_gem_match(message)
        if intent == "route_explanation":
            return self._answer_route_explanation()
        if intent == "eco_reward_help":
            return self._answer_eco_reward_help()
        if intent == "crowded_places":
            return self._answer_crowded_places()
        return self._answer_faq_or_fallback(message)

    def _answer_nearby_low_crowd(self, message: str) -> str:
        source = self._resolve_context_attraction(message)
        if source is not None:
            recommendations = self.retrieval_service.get_hidden_gems(source, preference="gần, ít đông", top_k=3)
            if recommendations:
                lines = [f"Nếu bạn muốn tránh đông quanh {source['name']}, mình gợi ý 3 điểm sau:"]
                for item in recommendations:
                    lines.append(
                        f"- {item['name']} | {item['category']} | cách khoảng {float(item['distance_km']):.1f} km | "
                        f"crowd {item['crowd_score']} | rating {float(item['rating']):.1f}"
                    )
                lines.append("Đây là các điểm đang dễ thở hơn ở thời điểm mô phỏng hiện tại.")
                return "\n".join(lines)

        low_crowd_places = self.retrieval_service.get_low_crowd_places(limit=3)
        if not low_crowd_places:
            return "Hiện mình chưa đọc được dữ liệu attraction để gợi ý điểm ít đông."

        lines = ["Mình chưa xác định được điểm mốc cụ thể, nhưng đây là các điểm đang khá dễ đi trong dữ liệu hiện tại:"]
        for item in low_crowd_places:
            lines.append(
                f"- {item['name']} | {item['category']} | khu vực {item['area']} | crowd {item['crowd_score']} | rating {float(item.get('avg_rating', 0.0)):.1f}"
            )
        return "\n".join(lines)

    def _answer_best_visit_time(self, message: str) -> str:
        attraction = self._resolve_context_attraction(message)
        if attraction is None:
            return "Bạn hãy nêu rõ tên địa điểm, ví dụ: 'Nên đi Bảo tàng Đà Nẵng lúc mấy giờ?' để mình tư vấn chính xác hơn."

        best_visit = self.retrieval_service.get_best_visit_time(attraction)
        current_score = self.retrieval_service.get_current_crowd_score(attraction)
        score_explanation = self.retrieval_service.explain_crowd_score(attraction)

        if best_visit.get("datetime") is None:
            return (
                f"Hiện mình chưa có dự báo theo giờ cho {attraction['name']}. "
                f"Crowd hiện tại đang khoảng {current_score}/100, mức {self.retrieval_service.level_vi(current_score)}."
            )

        best_time = best_visit["datetime"].strftime("%d/%m %H:%M")
        return (
            f"Khung giờ mình gợi ý để đi {attraction['name']} là khoảng {best_time}. "
            f"Dự báo crowd lúc đó khoảng {best_visit['crowd_score']}/100, mức {self.retrieval_service.level_vi(int(best_visit['crowd_score']))}.\n\n"
            f"Hiện tại điểm này đang ở mức {current_score}/100. "
            f"Lý do mô phỏng chính: {score_explanation}."
        )

    def _answer_hidden_gem_match(self, message: str) -> str:
        source = self._resolve_context_attraction(message)
        if source is None:
            return "Bạn có thể hỏi theo mẫu như 'Hidden gem nào phù hợp gần Cầu Rồng?' hoặc sau khi tạo planner mình sẽ dùng luôn điểm đến gần nhất làm ngữ cảnh."

        preference = self._extract_preference(message)
        recommendations = self.retrieval_service.get_hidden_gems(source, preference=preference, top_k=3)
        if not recommendations:
            return f"Hiện mình chưa tìm được hidden gem phù hợp quanh {source['name']} với dữ liệu mô phỏng hiện tại."

        lines = [f"Các hidden gem phù hợp gần {source['name']}:"]
        for item in recommendations:
            lines.append(
                f"- {item['name']} | {item['category']} | cách {float(item['distance_km']):.1f} km | "
                f"crowd {item['crowd_score']} | rating {float(item['rating']):.1f}\n  Lý do: {item['reason']}"
            )
        return "\n".join(lines)

    def _answer_route_explanation(self) -> str:
        route_result = self.last_planner_result or {}
        best_route = route_result.get("best_route")
        if best_route is None:
            return "Hiện chatbot chưa có route nào từ Planner để giải thích. Bạn hãy vào trang Lập kế hoạch, bấm 'Đề xuất tuyến', rồi quay lại hỏi mình."

        alternative_routes = route_result.get("alternative_routes", [])
        better_than = ""
        if alternative_routes:
            first_alt = alternative_routes[0]
            better_than = (
                f" So với phương án thay thế gần nhất, tuyến này có route score {best_route['route_score']} "
                f"so với {first_alt['route_score']}, thời gian {best_route['travel_time']} phút "
                f"và phát thải {best_route['estimated_carbon_g']} g CO2."
            )

        return (
            f"Tuyến được chọn là {best_route['route_name']} vì nó hợp chiến lược {route_result.get('strategy', 'cân bằng')} nhất trong các phương án hiện có. "
            f"Tuyến này mất khoảng {best_route['travel_time']} phút, crowd tại điểm đến là {best_route['crowd_score_destination']}/100, "
            f"carbon footprint khoảng {best_route['estimated_carbon_g']} g CO2 và eco score đạt {best_route['eco_score']}/100."
            f"{better_than}\n\n"
            f"Giải thích chi tiết từ planner: {best_route['explanation']}"
        )

    def _answer_eco_reward_help(self) -> str:
        rules = self.retrieval_service.get_reward_rules()
        wallet_summary = None
        if self.eco_reward_service is not None:
            wallet_summary = self.eco_reward_service.get_wallet_summary(settings.DEFAULT_USER_ID)

        if not rules:
            return "Hiện mình chưa đọc được rule Eco Reward, nhưng nhìn chung bạn sẽ được thưởng nhiều hơn khi đi bộ, đi xe đạp, chọn giờ thấp điểm và ưu tiên hidden gem."

        lines = ["Để tích điểm xanh, bạn nên ưu tiên các hành động sau:"]
        for item in rules[:5]:
            lines.append(
                f"- {item['action_type']}: +{int(item['point_value'])} điểm. {str(item.get('description', '')).strip()}"
            )
        if wallet_summary is not None:
            lines.append(f"Tổng eco points hiện tại của user local là {wallet_summary['total_points']} điểm.")
        lines.append("Trong Planner, sau khi xác nhận route, bạn có thể bấm 'Nhận Eco Reward' để cộng điểm vào SQLite local.")
        return "\n".join(lines)

    def _answer_crowded_places(self) -> str:
        crowded_places = self.retrieval_service.get_crowded_places(limit=3)
        if not crowded_places:
            return "Hiện mình chưa đọc được dữ liệu crowd để xác định điểm nào đang đông."

        lines = ["Các điểm đang có crowd cao nhất ở trạng thái mô phỏng hiện tại là:"]
        for item in crowded_places:
            lines.append(
                f"- {item['name']} | khu vực {item['area']} | crowd {item['crowd_score']}/100 | mức {self.retrieval_service.level_vi(int(item['crowd_score']))}"
            )
        lines.append("Bạn có thể mở Dashboard để xem bảng chi tiết và bấm Refresh nếu vừa đổi trạng thái ở Admin Simulation.")
        return "\n".join(lines)

    def _answer_faq_or_fallback(self, message: str) -> str:
        faq_item = self.retrieval_service.search_faq(message)
        if faq_item is not None:
            follow_up = self._faq_follow_up(faq_item.intent, message)
            return f"{faq_item.answer}\n\n{follow_up}" if follow_up else faq_item.answer

        return (
            "Mình chưa hiểu đủ ý câu hỏi này. Bạn có thể hỏi lại theo các mẫu như:\n"
            "- Điểm nào gần mà ít đông?\n"
            "- Nên đi Bảo tàng Đà Nẵng lúc mấy giờ?\n"
            "- Hidden gem nào phù hợp gần Cầu Rồng?\n"
            "- Vì sao route này được chọn?\n"
            "- Làm sao để tích điểm xanh?\n"
            "- Địa điểm nào đang đông?"
        )

    def _faq_follow_up(self, faq_intent: str, message: str) -> str:
        normalized_intent = faq_intent.casefold()
        if "hidden" in normalized_intent:
            return self._answer_hidden_gem_match(message)
        if "đông" in normalized_intent or "crowd" in normalized_intent:
            return self._answer_crowded_places()
        if "reward" in normalized_intent or "eco" in normalized_intent:
            return self._answer_eco_reward_help()
        if "giờ" in normalized_intent or "time" in normalized_intent:
            return self._answer_best_visit_time(message)
        return ""

    def _resolve_context_attraction(self, message: str) -> dict[str, Any] | None:
        from_message = self.retrieval_service.find_attraction(message)
        if from_message is not None:
            return from_message

        planner_destination = (self.last_planner_result or {}).get("destination", {})
        destination_id = str(planner_destination.get("id", "")).strip()
        if destination_id:
            from_planner = self.retrieval_service.get_attraction_by_id(destination_id)
            if from_planner is not None:
                return from_planner

        planner_origin = (self.last_planner_result or {}).get("origin", {})
        origin_id = str(planner_origin.get("id", "")).strip()
        if origin_id:
            return self.retrieval_service.get_attraction_by_id(origin_id)
        return None

    @staticmethod
    def _extract_preference(message: str) -> str | None:
        normalized = message.casefold()
        for keyword in ["thiên nhiên", "văn hóa", "ẩm thực", "check-in", "thư giãn", "lịch sử", "ít đông", "gần"]:
            if keyword in normalized:
                return keyword
        return None
