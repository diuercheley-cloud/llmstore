import logging

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ModerationPolicyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_message(self, content: str) -> bool:
        # Basic check for toxic content or forbidden words
        forbidden_words = ["badword1", "badword2"]  # Placeholder
        for word in forbidden_words:
            if word in content.lower():
                return False
        return True

    async def flag_message(self, message_id: str, reason: str):
        # Implementation to flag a message for admin review
        logger.info(f"Message {message_id} flagged for: {reason}")
        pass
