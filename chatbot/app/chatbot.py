from dotenv import load_dotenv
import os
from google import genai
from flask_login import current_user
from flask import url_for, session
from app import db
from app.models import Message

load_dotenv()
api_key = os.environ["GOOGLE_API_KEY"]
client = genai.Client(api_key=api_key)

FAQ_RESPONSES: dict[str,str] = {
    "how do i clear the conversation history?":
       "Visit the 'account' page.",
    "can i make an appointment?":
       "Yes. Please follow the procedures to book your session.",
    "can i speak to a human agent?":
       "Yes. A human operator will be in contact soon."
}
def get_bot_response(user_input):
    user_message_lower = user_input.lower()

    if user_message_lower in FAQ_RESPONSES:
        return FAQ_RESPONSES[user_message_lower]

    elif "faq" in user_message_lower:
        return f"You can find the faq section here: {url_for('faq', _external=True)}"
    elif "support" in user_message_lower:
        return "If you need support, please contact us at support@uniss.com."

    elif "review" in user_message_lower:
        return f"You can leave a review here: {url_for('review', _external=True)}"
    elif "report" in user_message_lower:
        if current_user.is_authenticated and hasattr(current_user, 'role') and current_user.role == 'admin':
            return f"You can access the trend report here: {url_for('trend_report', _external=True)}"
        else:
            return "Only administrators can access the trend report."
    else:
        response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=user_input,
        )
        return response.text

def chat_and_log(user_input):
    bot_reply = get_bot_response(user_input)
    conv_id = session.get("conversation_id")
    if conv_id:
        db.session.add_all(
            [
                Message(conversation_id=conv_id, sender_id=current_user.id, role='user', content=user_input),
                Message(conversation_id=conv_id, sender_id=None, role='bot', content=bot_reply),
            ]
        )
        db.session.commit()
    return bot_reply