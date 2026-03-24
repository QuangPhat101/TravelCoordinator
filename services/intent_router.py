from __future__ import annotations


class IntentRouter:
    def detect_intent(self, message: str) -> str:
        normalized = message.strip().casefold()
        if not normalized:
            return "empty"

        if any(keyword in normalized for keyword in ["xin chào", "hello", "hi", "chào"]):
            return "greeting"
        if any(
            keyword in normalized
            for keyword in [
                "điểm nào gần",
                "gần mà ít đông",
                "gần và ít đông",
                "gần chỗ này",
                "tránh chỗ đông",
            ]
        ):
            return "nearby_low_crowd"
        if any(
            keyword in normalized
            for keyword in [
                "nên đi lúc mấy giờ",
                "đi lúc mấy giờ",
                "khi nào nên đi",
                "giờ nào",
                "khung giờ nào",
            ]
        ):
            return "best_visit_time"
        if any(
            keyword in normalized
            for keyword in [
                "hidden gem",
                "ẩn",
                "bí mật",
                "phù hợp",
                "gợi ý chỗ khác",
            ]
        ):
            return "hidden_gem_match"
        if any(
            keyword in normalized
            for keyword in [
                "vì sao route",
                "vì sao tuyến",
                "route này",
                "tuyến này",
                "tại sao chọn",
            ]
        ):
            return "route_explanation"
        if any(
            keyword in normalized
            for keyword in [
                "tích điểm xanh",
                "eco reward",
                "điểm xanh",
                "điểm thưởng",
                "eco points",
            ]
        ):
            return "eco_reward_help"
        if any(
            keyword in normalized
            for keyword in [
                "đang đông",
                "địa điểm nào đông",
                "mật độ",
                "crowd",
                "quá tải",
            ]
        ):
            return "crowded_places"
        return "faq_or_fallback"
