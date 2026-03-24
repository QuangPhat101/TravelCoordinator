from __future__ import annotations

import csv
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

try:
    import pandas as pd
except ImportError:  # pragma: no cover - fallback keeps the script runnable before dependencies are installed.
    pd = None


BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLE_DIR = BASE_DIR / "data" / "sample"


def generate_attractions() -> list[dict[str, object]]:
    return [
        {
            "attraction_id": "DN001",
            "name": "Cầu Rồng",
            "category": "check-in",
            "description": "Biểu tượng của Đà Nẵng, nổi bật vào buổi tối và cuối tuần.",
            "latitude": 16.0614,
            "longitude": 108.2278,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "00:00-23:59",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.7,
            "estimated_capacity": 5000,
            "popularity_score": 95,
            "indoor_outdoor": "outdoor",
            "tags": "cầu|ban đêm|sông Hàn|check-in",
        },
        {
            "attraction_id": "DN002",
            "name": "Cầu Tình Yêu",
            "category": "check-in",
            "description": "Điểm dạo bộ ven sông, phù hợp ngắm cảnh và chụp ảnh.",
            "latitude": 16.0618,
            "longitude": 108.2292,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "06:00-23:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.5,
            "estimated_capacity": 2200,
            "popularity_score": 82,
            "indoor_outdoor": "outdoor",
            "tags": "ven sông|chụp ảnh|cặp đôi|check-in",
        },
        {
            "attraction_id": "DN003",
            "name": "Bảo tàng Điêu khắc Chăm",
            "category": "bảo tàng",
            "description": "Không gian lưu giữ bộ sưu tập điêu khắc Chăm lớn và giàu giá trị lịch sử.",
            "latitude": 16.0604,
            "longitude": 108.2237,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "07:00-17:30",
            "ticket_price": "60.000 VNĐ",
            "avg_rating": 4.6,
            "estimated_capacity": 1200,
            "popularity_score": 76,
            "indoor_outdoor": "indoor",
            "tags": "lịch sử|nghệ thuật|văn hóa Chăm|bảo tàng",
        },
        {
            "attraction_id": "DN004",
            "name": "Bảo tàng Đà Nẵng",
            "category": "bảo tàng",
            "description": "Giới thiệu tiến trình hình thành và phát triển của thành phố Đà Nẵng.",
            "latitude": 16.0728,
            "longitude": 108.2202,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "08:00-17:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.4,
            "estimated_capacity": 1500,
            "popularity_score": 62,
            "indoor_outdoor": "indoor",
            "tags": "thành phố|lịch sử|gia đình|bảo tàng",
        },
        {
            "attraction_id": "DN005",
            "name": "Chợ Hàn",
            "category": "ẩm thực",
            "description": "Khu chợ truyền thống nổi tiếng với đặc sản địa phương và quà lưu niệm.",
            "latitude": 16.0671,
            "longitude": 108.2233,
            "area": "Khu ẩm thực địa phương",
            "opening_hours": "06:00-19:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.3,
            "estimated_capacity": 3000,
            "popularity_score": 84,
            "indoor_outdoor": "indoor",
            "tags": "đặc sản|mua sắm|ẩm thực|chợ",
        },
        {
            "attraction_id": "DN006",
            "name": "Chợ Cồn",
            "category": "ẩm thực",
            "description": "Thiên đường ăn vặt địa phương với mật độ quầy hàng dày đặc.",
            "latitude": 16.0677,
            "longitude": 108.2122,
            "area": "Khu ẩm thực địa phương",
            "opening_hours": "07:00-18:30",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.5,
            "estimated_capacity": 3200,
            "popularity_score": 88,
            "indoor_outdoor": "indoor",
            "tags": "ăn vặt|địa phương|ẩm thực|đông khách",
        },
        {
            "attraction_id": "DN007",
            "name": "Công viên Biển Đông",
            "category": "thiên nhiên",
            "description": "Không gian mở sát biển, phù hợp tản bộ và quan sát chim bồ câu.",
            "latitude": 16.0678,
            "longitude": 108.2445,
            "area": "Sơn Trà ven biển",
            "opening_hours": "05:00-22:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.6,
            "estimated_capacity": 4000,
            "popularity_score": 79,
            "indoor_outdoor": "outdoor",
            "tags": "công viên|biển|đi bộ|gia đình",
        },
        {
            "attraction_id": "DN008",
            "name": "Bán đảo Sơn Trà",
            "category": "thiên nhiên",
            "description": "Khu sinh thái rừng và biển với nhiều điểm quan sát toàn cảnh thành phố.",
            "latitude": 16.1204,
            "longitude": 108.2685,
            "area": "Sơn Trà ven biển",
            "opening_hours": "06:00-17:30",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.8,
            "estimated_capacity": 3500,
            "popularity_score": 86,
            "indoor_outdoor": "outdoor",
            "tags": "rừng|cảnh quan|xe máy|thiên nhiên",
        },
        {
            "attraction_id": "DN009",
            "name": "Chùa Linh Ứng",
            "category": "văn hóa",
            "description": "Quần thể chùa linh thiêng với tượng Phật Quan Âm hướng biển.",
            "latitude": 16.0997,
            "longitude": 108.2775,
            "area": "Sơn Trà ven biển",
            "opening_hours": "06:00-21:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.8,
            "estimated_capacity": 2800,
            "popularity_score": 87,
            "indoor_outdoor": "outdoor",
            "tags": "tâm linh|toàn cảnh|văn hóa|tham quan",
        },
        {
            "attraction_id": "DN010",
            "name": "Ngũ Hành Sơn",
            "category": "thiên nhiên",
            "description": "Cụm núi đá vôi kết hợp hang động, chùa chiền và điểm ngắm cảnh.",
            "latitude": 16.0036,
            "longitude": 108.2645,
            "area": "Ngũ Hành Sơn",
            "opening_hours": "07:00-17:30",
            "ticket_price": "40.000 VNĐ",
            "avg_rating": 4.7,
            "estimated_capacity": 3000,
            "popularity_score": 83,
            "indoor_outdoor": "outdoor",
            "tags": "núi|hang động|tâm linh|thiên nhiên",
        },
        {
            "attraction_id": "DN011",
            "name": "Làng đá mỹ nghệ Non Nước",
            "category": "làng nghề",
            "description": "Làng nghề thủ công lâu đời, nổi tiếng với điêu khắc đá mỹ nghệ.",
            "latitude": 16.0048,
            "longitude": 108.2640,
            "area": "Ngũ Hành Sơn",
            "opening_hours": "08:00-18:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.5,
            "estimated_capacity": 1800,
            "popularity_score": 61,
            "indoor_outdoor": "indoor",
            "tags": "thủ công|đá mỹ nghệ|làng nghề|mua sắm",
        },
        {
            "attraction_id": "DN012",
            "name": "Bãi biển Mỹ Khê",
            "category": "thiên nhiên",
            "description": "Bãi biển nổi tiếng với cát mịn, phù hợp tắm biển và đi dạo.",
            "latitude": 16.0544,
            "longitude": 108.2478,
            "area": "Sơn Trà ven biển",
            "opening_hours": "04:30-20:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.8,
            "estimated_capacity": 6000,
            "popularity_score": 94,
            "indoor_outdoor": "outdoor",
            "tags": "biển|bình minh|thể thao biển|check-in",
        },
        {
            "attraction_id": "DN013",
            "name": "Nhà thờ Chính tòa Đà Nẵng",
            "category": "văn hóa",
            "description": "Công trình kiến trúc màu hồng nổi bật giữa trung tâm thành phố.",
            "latitude": 16.0679,
            "longitude": 108.2245,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "07:00-17:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.6,
            "estimated_capacity": 1400,
            "popularity_score": 77,
            "indoor_outdoor": "indoor",
            "tags": "kiến trúc|nhà thờ|check-in|văn hóa",
        },
        {
            "attraction_id": "DN014",
            "name": "Phố đi bộ Bạch Đằng",
            "category": "check-in",
            "description": "Trục đi bộ ven sông kết nối nhiều điểm ngắm cảnh và ẩm thực trung tâm.",
            "latitude": 16.0695,
            "longitude": 108.2246,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "05:00-23:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.5,
            "estimated_capacity": 4500,
            "popularity_score": 81,
            "indoor_outdoor": "outdoor",
            "tags": "đi bộ|ven sông|check-in|đêm",
        },
        {
            "attraction_id": "DN015",
            "name": "Công viên APEC",
            "category": "check-in",
            "description": "Không gian công cộng hiện đại với mái vòm cỏ nổi bật.",
            "latitude": 16.0594,
            "longitude": 108.2264,
            "area": "Trung tâm sông Hàn",
            "opening_hours": "05:00-22:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.6,
            "estimated_capacity": 2600,
            "popularity_score": 74,
            "indoor_outdoor": "outdoor",
            "tags": "kiến trúc|công viên|check-in|gia đình",
        },
        {
            "attraction_id": "DN016",
            "name": "Làng nước mắm Nam Ô",
            "category": "làng nghề",
            "description": "Điểm tìm hiểu nghề truyền thống gắn với văn hóa biển miền Trung.",
            "latitude": 16.1253,
            "longitude": 108.1242,
            "area": "Làng nghề ngoại ô",
            "opening_hours": "08:00-17:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.4,
            "estimated_capacity": 900,
            "popularity_score": 49,
            "indoor_outdoor": "indoor",
            "tags": "nước mắm|truyền thống|làng nghề|biển",
        },
        {
            "attraction_id": "DN017",
            "name": "Ghềnh Bàng",
            "category": "thiên nhiên",
            "description": "Bãi đá và làn nước trong, phù hợp du khách thích trải nghiệm thiên nhiên yên tĩnh.",
            "latitude": 16.1416,
            "longitude": 108.2412,
            "area": "Sơn Trà ven biển",
            "opening_hours": "06:00-17:00",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.7,
            "estimated_capacity": 1100,
            "popularity_score": 58,
            "indoor_outdoor": "outdoor",
            "tags": "trekking|biển|hoang sơ|hidden gem",
        },
        {
            "attraction_id": "DN018",
            "name": "Hải đăng Tiên Sa",
            "category": "check-in",
            "description": "Điểm ngắm biển và bán đảo từ trên cao, khá yên tĩnh vào sáng sớm.",
            "latitude": 16.1068,
            "longitude": 108.2710,
            "area": "Sơn Trà ven biển",
            "opening_hours": "06:00-17:30",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.5,
            "estimated_capacity": 1000,
            "popularity_score": 57,
            "indoor_outdoor": "outdoor",
            "tags": "ngắm cảnh|hải đăng|sơn trà|check-in",
        },
        {
            "attraction_id": "DN019",
            "name": "Làng chiếu Cẩm Nê",
            "category": "làng nghề",
            "description": "Không gian nghề truyền thống với sản phẩm chiếu thủ công đặc trưng.",
            "latitude": 15.9939,
            "longitude": 108.1460,
            "area": "Làng nghề ngoại ô",
            "opening_hours": "08:00-16:30",
            "ticket_price": "Miễn phí",
            "avg_rating": 4.4,
            "estimated_capacity": 700,
            "popularity_score": 42,
            "indoor_outdoor": "indoor",
            "tags": "chiếu cói|thủ công|làng nghề|truyền thống",
        },
        {
            "attraction_id": "DN020",
            "name": "Làng rau La Hường",
            "category": "văn hóa",
            "description": "Mô hình nông nghiệp đô thị xanh, phù hợp trải nghiệm cộng đồng nhỏ.",
            "latitude": 16.0393,
            "longitude": 108.1915,
            "area": "Làng nghề ngoại ô",
            "opening_hours": "07:00-17:00",
            "ticket_price": "30.000 VNĐ",
            "avg_rating": 4.5,
            "estimated_capacity": 850,
            "popularity_score": 46,
            "indoor_outdoor": "outdoor",
            "tags": "nông nghiệp|trải nghiệm|xanh|cộng đồng",
        },
    ]


def generate_crowd_history(attractions: list[dict[str, object]]) -> list[dict[str, object]]:
    rng = random.Random(20260323)
    start_date = datetime(2026, 3, 17)
    weather_cycle = ["nắng nhẹ", "nắng đẹp", "nhiều mây", "mưa nhẹ", "nắng đẹp", "mưa rào", "nắng nhẹ"]
    temperature_cycle = [28, 30, 29, 26, 31, 27, 29]
    category_bonus = {
        "văn hóa": 5,
        "thiên nhiên": 8,
        "ẩm thực": 14,
        "bảo tàng": 4,
        "check-in": 11,
        "làng nghề": -2,
    }

    rows: list[dict[str, object]] = []
    for day_offset in range(7):
        current_day = start_date + timedelta(days=day_offset)
        weather = weather_cycle[day_offset]
        temperature = temperature_cycle[day_offset]
        rain_flag = 1 if "mưa" in weather else 0
        holiday_flag = 1 if current_day.weekday() >= 5 else 0

        for hour in range(6, 22):
            is_evening_event = 1 if current_day.weekday() in {4, 5} and 18 <= hour <= 21 else 0
            for attraction in attractions:
                popularity_score = int(attraction["popularity_score"])
                category = str(attraction["category"])
                indoor_outdoor = str(attraction["indoor_outdoor"])
                area = str(attraction["area"])

                hour_bonus = 0
                if category == "ẩm thực" and hour in {11, 12, 18, 19, 20}:
                    hour_bonus += 18
                if category == "check-in" and hour in {17, 18, 19, 20}:
                    hour_bonus += 16
                if category == "thiên nhiên" and hour in {6, 7, 8, 15, 16, 17}:
                    hour_bonus += 14
                if category == "bảo tàng" and hour in {9, 10, 14, 15}:
                    hour_bonus += 10
                if category == "văn hóa" and hour in {8, 9, 16, 17}:
                    hour_bonus += 8

                weekend_bonus = 10 if holiday_flag else 0
                event_bonus = 9 if is_evening_event and area == "Trung tâm sông Hàn" else 0
                rain_adjustment = 5 if rain_flag and indoor_outdoor == "indoor" else -12 if rain_flag else 0
                temperature_adjustment = 4 if temperature >= 30 and indoor_outdoor == "outdoor" and hour >= 11 else 0
                noise = rng.randint(-6, 6)

                crowd_score = (
                    popularity_score * 0.52
                    + category_bonus.get(category, 0)
                    + hour_bonus
                    + weekend_bonus
                    + event_bonus
                    + rain_adjustment
                    + temperature_adjustment
                    + noise
                )
                crowd_score = max(8, min(98, int(round(crowd_score))))

                timestamp = current_day.replace(hour=hour, minute=0, second=0)
                rows.append(
                    {
                        "timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                        "attraction_id": attraction["attraction_id"],
                        "crowd_score": crowd_score,
                        "weather": weather,
                        "temperature": temperature,
                        "rain_flag": rain_flag,
                        "holiday_flag": holiday_flag,
                        "event_flag": is_evening_event,
                        "day_of_week": current_day.strftime("%A"),
                        "hour": hour,
                    }
                )
    return rows


def generate_transport_options(attractions: list[dict[str, object]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, origin in enumerate(attractions):
        for destination in attractions[index + 1 :]:
            distance = round(
                haversine_km(
                    float(origin["latitude"]),
                    float(origin["longitude"]),
                    float(destination["latitude"]),
                    float(destination["longitude"]),
                ),
                2,
            )
            options: list[tuple[str, int, int]] = []

            if distance <= 3.2:
                options.append(("đi bộ", max(8, int(distance / 4.6 * 60) + 3), 0))
            if distance <= 7.5:
                options.append(("xe đạp", max(6, int(distance / 12.0 * 60) + 4), 0))
            if distance <= 25.0:
                options.append(("xe bus", max(10, int(distance / 18.0 * 60) + 8), int(distance * 28)))
            options.append(("taxi", max(7, int(distance / 24.0 * 60) + 6), int(distance * 170)))

            for mode, duration, carbon in options:
                rows.append(
                    {
                        "origin_id": origin["attraction_id"],
                        "destination_id": destination["attraction_id"],
                        "transport_mode": mode,
                        "distance_km": distance,
                        "duration_min": duration,
                        "estimated_carbon_g": carbon,
                    }
                )
                rows.append(
                    {
                        "origin_id": destination["attraction_id"],
                        "destination_id": origin["attraction_id"],
                        "transport_mode": mode,
                        "distance_km": distance,
                        "duration_min": duration,
                        "estimated_carbon_g": carbon,
                    }
                )
    return rows


def generate_eco_rewards() -> list[dict[str, object]]:
    return [
        {
            "rule_id": "ER001",
            "action_type": "Đi xe bus giữa các điểm tham quan",
            "point_value": 12,
            "condition": "Chọn xe bus thay cho taxi trong hành trình nội đô",
            "description": "Khuyến khích du khách dùng phương tiện công cộng để giảm phát thải.",
        },
        {
            "rule_id": "ER002",
            "action_type": "Đi bộ khám phá cụm trung tâm",
            "point_value": 8,
            "condition": "Đi bộ ít nhất 1 km giữa hai điểm gần nhau",
            "description": "Áp dụng khi di chuyển trong khu vực ven sông Hàn hoặc trung tâm thành phố.",
        },
        {
            "rule_id": "ER003",
            "action_type": "Đi xe đạp ven biển",
            "point_value": 10,
            "condition": "Chọn xe đạp cho chặng ngắn dưới 7.5 km",
            "description": "Tăng điểm thưởng khi ưu tiên phương tiện phát thải thấp.",
        },
        {
            "rule_id": "ER004",
            "action_type": "Mang bình nước cá nhân",
            "point_value": 6,
            "condition": "Không mua chai nhựa dùng một lần trong ngày tham quan",
            "description": "Giảm lượng rác thải nhựa phát sinh trong suốt hành trình.",
        },
        {
            "rule_id": "ER005",
            "action_type": "Ghép lịch vào khung giờ ít đông",
            "point_value": 9,
            "condition": "Tham quan ngoài khung giờ đỉnh tại điểm có crowd score cao",
            "description": "Hỗ trợ phân tán khách, giảm quá tải cục bộ tại điểm nóng.",
        },
        {
            "rule_id": "ER006",
            "action_type": "Mua sản phẩm làng nghề địa phương",
            "point_value": 7,
            "condition": "Mua hàng trực tiếp tại làng nghề trong khu demo",
            "description": "Khuyến khích chi tiêu cho cộng đồng địa phương và sản phẩm thủ công.",
        },
        {
            "rule_id": "ER007",
            "action_type": "Ghé thăm hidden gem ít đông",
            "point_value": 11,
            "condition": "Chọn điểm có popularity score dưới 60",
            "description": "Phân tán dòng khách sang các điểm bền vững hơn và ít áp lực hơn.",
        },
        {
            "rule_id": "ER008",
            "action_type": "Tham gia dọn rác cộng đồng",
            "point_value": 15,
            "condition": "Tham gia hoạt động làm sạch bãi biển hoặc công viên",
            "description": "Điểm thưởng cao cho hành động đóng góp trực tiếp vào môi trường du lịch.",
        },
    ]


def generate_faq() -> list[dict[str, object]]:
    return [
        {
            "question": "Điểm nào ít đông",
            "intent": "low_crowd_recommendation",
            "answer": "Các điểm thường ít đông hơn trong bộ demo là Ghềnh Bàng, Hải đăng Tiên Sa, Làng chiếu Cẩm Nê và Làng nước mắm Nam Ô.",
            "tags": "ít đông|vắng khách|hidden gem|gợi ý",
        },
        {
            "question": "Nên đi lúc mấy giờ",
            "intent": "best_visit_time",
            "answer": "Khung 7:00-9:00 và 14:00-16:00 thường dễ chịu hơn và ít áp lực khách hơn ở phần lớn điểm tham quan.",
            "tags": "giờ đi|thời gian|khi nào|đỡ đông",
        },
        {
            "question": "Có bus không",
            "intent": "bus_availability",
            "answer": "Có. Bộ dữ liệu mẫu có các lựa chọn xe bus giữa nhiều điểm chính trong thành phố để planner ưu tiên hành trình xanh.",
            "tags": "bus|xe buýt|phương tiện|công cộng",
        },
        {
            "question": "Hidden gem là gì",
            "intent": "hidden_gem_explain",
            "answer": "Hidden gem là những điểm có chất lượng trải nghiệm tốt nhưng mức độ phổ biến và áp lực khách thấp hơn các điểm biểu tượng.",
            "tags": "hidden gem|điểm ẩn|ít nổi tiếng|ít đông",
        },
        {
            "question": "Eco reward dùng để làm gì",
            "intent": "eco_reward_info",
            "answer": "Eco Reward ghi nhận các hành vi xanh như đi bus, đi bộ, mang bình nước cá nhân hoặc ghé điểm ít đông để cộng điểm thưởng.",
            "tags": "eco reward|điểm thưởng|điểm xanh|phần thưởng",
        },
        {
            "question": "Du lịch xanh là gì",
            "intent": "green_travel_definition",
            "answer": "Du lịch xanh là cách đi ưu tiên phát thải thấp, tôn trọng cộng đồng địa phương và giảm áp lực lên điểm đến quá tải.",
            "tags": "du lịch xanh|bền vững|môi trường|eco",
        },
        {
            "question": "Điểm nào phù hợp gia đình",
            "intent": "family_friendly",
            "answer": "Công viên Biển Đông, Công viên APEC, Bảo tàng Điêu khắc Chăm và Bãi biển Mỹ Khê là các lựa chọn phù hợp gia đình trong bộ demo.",
            "tags": "gia đình|trẻ em|nhẹ nhàng|an toàn",
        },
        {
            "question": "Có điểm làng nghề nào",
            "intent": "craft_village_info",
            "answer": "Bạn có thể ghé Làng đá mỹ nghệ Non Nước, Làng nước mắm Nam Ô hoặc Làng chiếu Cẩm Nê để trải nghiệm làng nghề.",
            "tags": "làng nghề|thủ công|địa phương|truyền thống",
        },
        {
            "question": "Mưa thì nên đi đâu",
            "intent": "rainy_day_recommendation",
            "answer": "Khi mưa, nên ưu tiên các điểm trong nhà như Bảo tàng Điêu khắc Chăm, Bảo tàng Đà Nẵng, Chợ Hàn hoặc Chợ Cồn.",
            "tags": "mưa|trong nhà|indoor|thời tiết xấu",
        },
        {
            "question": "Có nên đi taxi không",
            "intent": "taxi_tradeoff",
            "answer": "Taxi vẫn có trong dữ liệu mẫu, nhưng planner sẽ ưu tiên đi bộ, xe đạp hoặc xe bus nếu bạn chọn mục tiêu giảm phát thải.",
            "tags": "taxi|carbon|phát thải|planner",
        },
    ]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(d_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius * c


def write_dataset(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pd is not None:
        pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")
        return

    with path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

    attractions = generate_attractions()
    crowd_history = generate_crowd_history(attractions)
    transport_options = generate_transport_options(attractions)
    eco_rewards = generate_eco_rewards()
    faq_knowledge_base = generate_faq()

    write_dataset(attractions, SAMPLE_DIR / "attractions.csv")
    write_dataset(crowd_history, SAMPLE_DIR / "crowd_history.csv")
    write_dataset(transport_options, SAMPLE_DIR / "transport_options.csv")
    write_dataset(eco_rewards, SAMPLE_DIR / "eco_rewards.csv")
    write_dataset(faq_knowledge_base, SAMPLE_DIR / "faq_knowledge_base.csv")

    print(f"Da tao du lieu mau tai: {SAMPLE_DIR}")
    print(f"So dia diem: {len(attractions)}")
    print(f"So ban ghi crowd history: {len(crowd_history)}")
    print(f"So tuy chon di chuyen: {len(transport_options)}")


if __name__ == "__main__":
    main()
