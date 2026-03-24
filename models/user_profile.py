from dataclasses import dataclass


@dataclass(slots=True)
class UserProfile:
    user_id: str
    display_name: str
    email: str
    avatar_path: str = ""
    created_at: str = ""
    last_login_at: str = ""
