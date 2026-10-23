# """Step 3: Multi-turn Conversational Support Agent for ZentroMart.

# Implements context memory, caller verification, policy enforcement,
# mock tool integration (lookup_order, create_ticket), and human handovers.
# """
# import re
# import sys
# from typing import Dict, List, Optional, Any

# from .config import DATASET_ROOT, REFERENCE_DATE
# from .rag import answer_with_rag, get_retriever
# from .llm import generate_text

# # Add tools directory to path to import synthetic tools
# sys.path.insert(0, str(DATASET_ROOT / "tools"))
# try:
#     from tools import lookup_order, create_ticket
# except ImportError:
#     def lookup_order(order_id: str, verification_value: str = None) -> dict:
#         return {"verification_required": True}
#     def create_ticket(summary: str, order_id: str = None, reason: str = None, intent: str = None) -> dict:
#         return {"created": True, "ticket_id": "TKT_MOCK"}


# AGENT_CONV_SYSTEM_PROMPT = (
#     "You are the customer support AI assistant for ZentroMart, an Indian online store "
#     "selling groceries and electronics. Today is 20 October 2026.\n\n"
#     "CRITICAL CONVERSATIONAL GUIDELINES:\n"
#     "1. Introduce yourself as an AI assistant on the very first turn.\n"
#     "2. Before disclosing order details, verify caller with their phone last 4 digits or pincode.\n"
#     "3. When order is verified:\n"
#     "   - For delivery status: state promised delivery date. If past promised date, apologize politely (e.g., 'I apologize for the delay').\n"
#     "   - For return eligibility: check delivered_on date and return window (electronics: 7 days, fashion: 15 days, BUT orders placed 1 to 15 October festive sale get 30 days!). State the exact return deadline date. Note that ZentroMart Plus members have free returns, whereas non-Plus members pay ₹49.\n"
#     "   - For refund status: if return is picked up, state that quality check (QC) is pending. If refund is overdue beyond 3 business days, provide the RRN and escalate.\n"
#     "   - For damage/defect on items >= ₹10,000, repeat contact (contacts_last_7_days >= 2), or customer explicitly requesting a person/human: create a ticket and escalate to Priority Resolution / human colleague.\n"
#     "4. Reply in the same language as customer (English, Hindi, or Hinglish). Keep answers concise and spoken-friendly.\n"
#     "5. Do NOT re-introduce yourself or say 'Namaste' / 'Hello' after the first turn. Jump straight to the answer."
# )


# class SupportAgent:
#     """Conversational Customer Support Agent for ZentroMart."""

#     def __init__(self, conversation_id: str = "conv_default"):
#         self.conversation_id = conversation_id
#         self.history: List[Dict[str, str]] = []
#         self.order_id: Optional[str] = None
#         self.verified: bool = False
#         self.order_data: Optional[Dict[str, Any]] = None
#         self.verification_attempts: int = 0
#         self.escalated: bool = False
#         self.last_ticket_id: Optional[str] = None

#     def _extract_digits(self, text: str) -> str:
#         """Extract all consecutive or spaced digits."""
#         return "".join(ch for ch in text if "0" <= ch <= "9")

#     def _is_turn_1(self) -> bool:
#         return len(self.history) <= 1

#     def respond(self, message: str) -> str:
#         """Process incoming customer message and return agent's response."""
#         self.history.append({"role": "customer", "content": message})
#         msg_lower = message.lower()
#         extracted_nums = self._extract_digits(message)

#         # -------------------------------------------------------------
#         # TURN 1: Initial Greeting / Order Help
#         # -------------------------------------------------------------
#         if self._is_turn_1() and not self.order_id:
#             reply = (
#                 "Hello! I am your ZentroMart AI assistant. I'm here to help you. "
#                 "Could you please share your 8-digit order ID so I can assist you?"
#             )
#             self.history.append({"role": "assistant", "content": reply})
#             return reply

#         # -------------------------------------------------------------
#         # TURN 2: Order ID Provided (Caller Identity Verification Gate)
#         # -------------------------------------------------------------
#         if not self.order_id and len(extracted_nums) == 8:
#             self.order_id = extracted_nums
#             lookup_order(self.order_id)  # Unverified lookup call
#             reply = (
#                 f"Thank you. I have located order {self.order_id}. For your security, "
#                 "could you please verify your identity by providing either the last 4 digits "
#                 "of your registered phone number OR your 6-digit delivery pincode?"
#             )
#             self.history.append({"role": "assistant", "content": reply})
#             return reply

#         # -------------------------------------------------------------
#         # TURN 3: Verification Value Provided
#         # -------------------------------------------------------------
#         if self.order_id and not self.verified:
#             if len(extracted_nums) in (4, 6):
#                 verification_result = lookup_order(self.order_id, verification_value=extracted_nums)
#                 if verification_result.get("verified"):
#                     self.verified = True
#                     self.order_data = verification_result
#                     first_name = verification_result.get("customer_first_name", "Valued Customer")
#                     reply = (
#                         f"Thank you, {first_name}! Verification successful. "
#                         f"I can now access your order details. How can I help you with order {self.order_id} today?"
#                     )
#                     self.history.append({"role": "assistant", "content": reply})
#                     return reply
#                 else:
#                     self.verification_attempts += 1
#                     if self.verification_attempts >= 2:
#                         reply = (
#                             "I'm sorry, verification has failed. For security reasons, "
#                             "I cannot share details for this order. Please reach out to our team from your registered phone."
#                         )
#                     else:
#                         reply = "The verification details did not match. Please re-check and provide your phone's last 4 digits or pincode."
#                     self.history.append({"role": "assistant", "content": reply})
#                     return reply

#         # -------------------------------------------------------------
#         # ESCALATION TRIGGERS (ESC-1)
#         # -------------------------------------------------------------
#         human_requested = any(w in msg_lower for w in [
#             "human", "person", "agent", "colleague", "executive", "representative",
#             "इंसान", "सहयोगी", "baat kar sakti", "baat karni hai"
#         ])
        
#         repeat_contact = (
#             "third time" in msg_lower or "teesri baar" in msg_lower or
#             (self.order_data and int(self.order_data.get("contacts_last_7_days", 0)) >= 2)
#         )
        
#         high_value_damage = False
#         if self.order_data and any(w in msg_lower for w in ["damage", "defective", "kharab", "replacement", "crack", "broken"]):
#             items = self.order_data.get("items", [])
#             for it in items:
#                 price = int(it.get("unit_price_inr", 0))
#                 if price >= 10000:
#                     high_value_damage = True

#         fraud_reported = any(w in msg_lower for w in ["never placed", "fraud", "unauthorized", "didn't order"])

#         # Check for overdue refund escalation (> 3 business days overdue)
#         overdue_refund = False
#         rrn_to_share = ""
#         if self.order_data and ("refund" in msg_lower or "रिफ़ंड" in msg_lower):
#             initiated_on = self.order_data.get("return_refund_initiated_on") or self.order_data.get("cancellation_refund_initiated_on")
#             rrn_to_share = self.order_data.get("return_rrn") or self.order_data.get("cancellation_rrn") or ""
#             if initiated_on and initiated_on < "2026-10-10":  # clearly overdue relative to 20 Oct 2026
#                 overdue_refund = True

#         if human_requested or repeat_contact or high_value_damage or fraud_reported or overdue_refund:
#             reason = "human_requested" if human_requested else ("repeat_contact" if repeat_contact else ("overdue_refund" if overdue_refund else "high_value_damage"))
#             summary = (
#                 f"Escalation required: Order {self.order_id or 'N/A'}. Reason: {reason}. "
#                 f"Customer issue: {message}. Handing over to Priority Resolution team."
#             )
#             ticket_res = create_ticket(summary=summary, order_id=self.order_id, reason=reason)
#             if ticket_res.get("created"):
#                 self.last_ticket_id = ticket_res.get("ticket_id")
#                 extra_rrn = f" Here is your refund reference number (RRN): {rrn_to_share}." if rrn_to_share else ""
#                 reply = (
#                     f"I understand your concern.{extra_rrn} I have created a support ticket ({self.last_ticket_id}) "
#                     "and escalated your case to our Priority Resolution team / human colleague who will assist you shortly."
#                 )
#                 self.history.append({"role": "assistant", "content": reply})
#                 return reply

#         # -------------------------------------------------------------
#         # VERIFIED ORDER INQUIRIES (Dynamic Synthesis with LLM)
#         # -------------------------------------------------------------
#         if self.verified and self.order_data:
#             order_info = (
#                 f"Order ID: {self.order_id}\n"
#                 f"Status: {self.order_data.get('status')}\n"
#                 f"Placed At: {self.order_data.get('placed_at')}\n"
#                 f"Promised Date: {self.order_data.get('promised_date')}\n"
#                 f"Delivered On: {self.order_data.get('delivered_on')}\n"
#                 f"Payment Method: {self.order_data.get('payment_method')}\n"
#                 f"Is Plus Member: {self.order_data.get('is_plus')}\n"
#                 f"Return Status: {self.order_data.get('return_status')}\n"
#                 f"Return Reverse Pickup Fee: {self.order_data.get('return_reverse_pickup_fee_inr')}\n"
#                 f"Return QC Passed On: {self.order_data.get('return_qc_passed_on')}\n"
#                 f"Return Refund Initiated On: {self.order_data.get('return_refund_initiated_on')}\n"
#                 f"Items: {self.order_data.get('items')}\n"
#             )

#             # Retrieve grounded policy context for this specific question
#             rag_chunks = get_retriever().retrieve(message, top_k=3)
#             kb_context = "\n".join([f"[{c['section_id']}] {c['text']}" for c in rag_chunks])

#             prompt = (
#                 f"CALLER VERIFICATION STATUS: ALREADY FULLY VERIFIED. DO NOT ASK FOR IDENTITY/PHONE/PINCODE VERIFICATION AGAIN.\n\n"
#                 f"VERIFIED ORDER DATA:\n{order_info}\n\n"
#                 f"COMPANY POLICY CONTEXT:\n{kb_context}\n\n"
#                 f"CUSTOMER QUESTION:\n{message}\n\n"
#                 "Answer the customer's question directly and concisely based on the verified order data and policy above. "
#                 "If the customer asks about return eligibility or deadlines, provide the exact date (note: orders placed 1 to 15 October get a 30-day festive window!) "
#                 "and mention the pickup fee (₹49 for non-Plus, free for Plus). If asking about delivery, state the promised delivery date. "
#                 "If asking about refund, state the timeline for their payment method."
#             )

#             reply = generate_text(prompt, system_instruction=AGENT_CONV_SYSTEM_PROMPT, temperature=0.0)
#             self.history.append({"role": "assistant", "content": reply})
#             return reply

#         # -------------------------------------------------------------
#         # GENERAL POLICY / RAG GROUNDED QA
#         # -------------------------------------------------------------
#         rag_res = answer_with_rag(message)
#         reply = rag_res["response"]
#         self.history.append({"role": "assistant", "content": reply})
#         return reply
######################################################################################################################3

# """Step 3: Multi-turn Conversational Support Agent for ZentroMart.

# Implements context memory, caller verification, policy enforcement,
# mock tool integration (lookup_order, create_ticket), and human handovers.
# """
# import json
# import re
# import sys
# from typing import Dict, List, Optional, Any

# from .config import DATASET_ROOT, REFERENCE_DATE
# from .rag import answer_with_rag, get_retriever
# from .llm import generate_text

# # Add tools directory to path to import synthetic tools
# sys.path.insert(0, str(DATASET_ROOT / "tools"))
# try:
#     from tools import lookup_order, create_ticket
# except ImportError:
#     def lookup_order(order_id: str, verification_value: str = None) -> dict:
#         return {"verification_required": True}
#     def create_ticket(summary: str, order_id: str = None, reason: str = None, intent: str = None) -> dict:
#         return {"created": True, "ticket_id": "TKT_MOCK"}


# AGENT_CONV_SYSTEM_PROMPT = (
#     "You are the customer support AI assistant for ZentroMart, an Indian online store "
#     "selling groceries and electronics. Today is 20 October 2026.\n\n"
#     "RULES:\n"
#     "1. Never greet or re-introduce yourself (no 'Hello', 'Namaste', 'I am your AI assistant'). Jump straight to the answer.\n"
#     "2. When VERIFIED ORDER DATA is provided the caller is already verified. Never ask for identity details again.\n"
#     "3. Use ONLY the verified order data and the policy context. Never invent dates, amounts or policies. "
#     "If neither covers the question, say you do not have that information in store policies and offer a human colleague.\n"
#     "4. Delivery: state promised_date; if it is already past and the order is not delivered, apologize politely. "
#     "For 'when was it shipped' use shipped_on; for delivered use delivered_on. State exact dates.\n"
#     "5. Returns: check delivered_on and the return window (electronics 7 days, fashion 15 days, BUT orders placed 1 to 15 October "
#     "festive sale get 30 days). State the exact return deadline date. ZentroMart Plus members have free returns; non-Plus members pay Rs 49 pickup.\n"
#     "6. Refunds: if the return is picked up, say quality check (QC) is pending. If the refund is overdue beyond the policy timeline, give the RRN.\n"
#     "7. Cancellation: possible only before the order ships. If shipped_on is set or the status is shipped, out for delivery or delivered, "
#     "politely decline: the order can no longer be cancelled. Then explain the return option and state the return window in days from the policy context.\n"
#     "8. Compensation, voucher or goodwill requests: apologize first, say you cannot grant vouchers or cash compensation yourself, "
#     "and state only what policy provides (for example the express fee credit for late Express orders). Never promise or add any credit.\n"
#     "9. NEVER say or imply that you created a ticket or escalated, unless the context contains 'TICKET RAISED: <id>'. Tickets are created by the system, not by you.\n"
#     "10. Reply in the customer's language (English, Hindi or Hinglish). Be concise and spoken-friendly. "
#     "Plain text only: no markdown, no asterisks, no bullet symbols."
# )

# _MONTH_FIX = re.compile(r"\*+|^#+\s*", re.M)
# _LEADING_INTRO = re.compile(
#     r"^\s*(?:(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]*\s*)?"
#     r"(?:(?:i am|i'm|this is)\s+(?:your|the)\s+zentromart\s+ai(?:\s+customer\s+support)?\s+assistant|"
#     r"i am your ai assistant for zentromart)[.,!]?\s*",
#     re.I,
# )
# _LEADING_GREET = re.compile(r"^\s*(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]+\s*", re.I)

# # Words that mean the customer asked something specific (not just "I need help")
# _TOPIC_WORDS = [
#     "return", "refund", "cancel", "warranty", "deliver", "track", "where", "status", "damage", "defect",
#     "policy", "coupon", "price", "kab", "kahan", "wapas", "paisa", "replace", "exchange", "broken", "crack",
#     "late", "voucher", "compensation", "shipping", "ship", "payment", "upi", "card", "invoice", "gst",
#     "when", "how", "what", "can i", "do you", "kya", "kaise", "kitne", "?", "never placed", "fraud",
# ]


# def _is_generic_help(message: str) -> bool:
#     """True for openers like 'Hello, I need help with an order' that carry no specific question."""
#     m = message.lower()
#     if len(m.split()) > 14:
#         return False
#     if any(w in m for w in _TOPIC_WORDS):
#         return False
#     return True


# def _clean_reply(text: str, first_turn: bool) -> str:
#     text = text.replace("**", "").replace("__", "")
#     text = re.sub(r"^\s*[*#]+\s*", "", text, flags=re.M)
#     if not first_turn:
#         for _ in range(3):
#             new = _LEADING_INTRO.sub("", text, count=1)
#             new = _LEADING_GREET.sub("", new, count=1)
#             if new == text:
#                 break
#             text = new
#     return text.strip()


# class SupportAgent:
#     """Conversational Customer Support Agent for ZentroMart."""

#     def __init__(self, conversation_id: str = "conv_default"):
#         self.conversation_id = conversation_id
#         self.history: List[Dict[str, str]] = []
#         self.order_id: Optional[str] = None
#         self.verified: bool = False
#         self.order_data: Optional[Dict[str, Any]] = None
#         self.verification_attempts: int = 0
#         self.escalated: bool = False
#         self.last_ticket_id: Optional[str] = None
#         # Evidence for the UI and run.py logs (reset on every turn)
#         self.last_chunks: List[str] = []   # section ids retrieved this turn
#         self.last_sources: List[str] = []  # section ids the answer cited

#     # ------------------------------------------------------------------ helpers
#     def _extract_digits(self, text: str) -> str:
#         """Extract all consecutive or spaced digits."""
#         return "".join(ch for ch in text if "0" <= ch <= "9")

#     def _extract_order_id(self, text: str) -> Optional[str]:
#         """8-digit order id, either '8978 2837' / '89782837' or digits spoken one by one."""
#         m = re.search(r"\b(\d{4})[\s-]?(\d{4})\b", text)
#         if m:
#             return m.group(1) + m.group(2)
#         digits = self._extract_digits(text)
#         return digits if len(digits) == 8 else None

#     def _is_turn_1(self) -> bool:
#         return len(self.history) <= 1

#     def _finish(self, reply: str, first_turn: bool) -> str:
#         reply = _clean_reply(reply, first_turn)
#         self.history.append({"role": "assistant", "content": reply})
#         return reply

#     def _create_ticket(self, reason: str, message: str) -> Optional[str]:
#         summary = (
#             f"Escalation required: Order {self.order_id or 'N/A'}. Reason: {reason}. "
#             f"Customer issue: {message}. Handing over to Priority Resolution team."
#         )
#         res = create_ticket(summary=summary, order_id=self.order_id, reason=reason)
#         if res.get("created"):
#             self.last_ticket_id = res.get("ticket_id")
#             self.escalated = True
#             return self.last_ticket_id
#         return None

#     def _answer_from_order(self, message: str, just_verified: bool = False) -> str:
#         """LLM answer grounded in the verified order record + retrieved policy sections."""
#         customer_msgs = [h["content"] for h in self.history if h["role"] == "customer"]
#         retrieval_query = " ".join(customer_msgs[:-1])[:300] + " " + message if just_verified else message
#         chunks = get_retriever().retrieve(retrieval_query.strip(), top_k=3)
#         self.last_chunks = [c["section_id"] for c in chunks]
#         self.last_sources = list(self.last_chunks)
#         kb_context = "\n".join(f"[{c['section_id']}] {c['text']}" for c in chunks)
#         order_info = json.dumps(self.order_data, ensure_ascii=False, default=str, indent=1)
#         ticket_line = f"TICKET RAISED: {self.last_ticket_id}" if self.last_ticket_id else "No ticket has been raised."
#         convo = "\n".join(f"{h['role']}: {h['content']}" for h in self.history[-8:])

#         if just_verified:
#             first_name = self.order_data.get("customer_first_name", "")
#             task = (
#                 f"The caller has JUST been verified. Start with: 'Thank you, {first_name}, you are verified.' "
#                 "Then look at the conversation: if the customer already asked a specific question (for example where is my order, "
#                 "return, refund, cancellation), answer it now using the order data. If they only asked for general help, "
#                 "ask what they would like to know about the order. Do not greet."
#             )
#         else:
#             task = "Answer the customer's latest message directly and concisely."

#         prompt = (
#             "CALLER VERIFICATION STATUS: ALREADY FULLY VERIFIED.\n\n"
#             f"VERIFIED ORDER DATA (JSON):\n{order_info}\n\n"
#             f"COMPANY POLICY CONTEXT:\n{kb_context}\n\n"
#             f"SYSTEM STATUS: {ticket_line}\n\n"
#             f"CONVERSATION SO FAR:\n{convo}\n\n"
#             f"CUSTOMER LATEST MESSAGE:\n{message}\n\n{task}"
#         )
#         return generate_text(prompt, system_instruction=AGENT_CONV_SYSTEM_PROMPT, temperature=0.0)

#     # ------------------------------------------------------------------ main
#     def respond(self, message: str) -> str:
#         """Process incoming customer message and return agent's response."""
#         self.history.append({"role": "customer", "content": message})
#         self.last_chunks, self.last_sources = [], []
#         first_turn = self._is_turn_1()
#         msg_lower = message.lower()
#         extracted_nums = self._extract_digits(message)

#         # TURN 1: generic opener -> greet and ask for order id.
#         # A specific first question (e.g. "What is the return window for electronics?") is answered below instead.
#         if first_turn and not self.order_id and not self._extract_order_id(message) and _is_generic_help(message):
#             return self._finish(
#                 "Hello! I am your ZentroMart AI assistant. I'm here to help you. "
#                 "Could you please share your 8-digit order ID so I can assist you?", True)

#         # TURN 2: order id provided -> identity verification gate
#         if not self.order_id:
#             oid = self._extract_order_id(message)
#             if oid:
#                 self.order_id = oid
#                 lookup_order(self.order_id)  # unverified lookup call
#                 return self._finish(
#                     f"Thank you. I have located order {self.order_id}. For your security, "
#                     "could you please verify your identity by providing either the last 4 digits "
#                     "of your registered phone number OR your 6-digit delivery pincode?", first_turn)

#         # TURN 3: verification value provided
#         if self.order_id and not self.verified and len(extracted_nums) in (4, 6):
#             result = lookup_order(self.order_id, verification_value=extracted_nums)
#             if result.get("verified"):
#                 self.verified = True
#                 self.order_data = result
#                 first_name = result.get("customer_first_name", "Valued Customer")
#                 try:
#                     reply = self._answer_from_order(message, just_verified=True)
#                 except Exception:
#                     reply = (f"Thank you, {first_name}! Verification successful. "
#                              f"How can I help you with order {self.order_id} today?")
#                 return self._finish(reply, False)
#             self.verification_attempts += 1
#             if self.verification_attempts >= 2:
#                 reply = ("I'm sorry, verification has failed. For security reasons, "
#                          "I cannot share details for this order. Please reach out to our team from your registered phone.")
#             else:
#                 reply = "The verification details did not match. Please re-check and provide your phone's last 4 digits or pincode."
#             return self._finish(reply, first_turn)

#         # ESCALATION TRIGGERS (ESC-1..ESC-4) - decided in code, never by the LLM
#         human_requested = any(w in msg_lower for w in [
#             "human", "person", "agent", "colleague", "executive", "representative",
#             "इंसान", "सहयोगी", "baat kar sakti", "baat karni hai"])

#         repeat_contact = (not self.escalated) and (
#             "third time" in msg_lower or "teesri baar" in msg_lower or
#             bool(self.order_data and int(self.order_data.get("contacts_last_7_days") or 0) >= 2))

#         high_value_damage = False
#         if self.order_data and any(w in msg_lower for w in ["damage", "defective", "kharab", "replacement", "crack", "broken"]):
#             for it in self.order_data.get("items", []):
#                 if int(float(it.get("unit_price_inr") or 0)) >= 10000:
#                     high_value_damage = True

#         fraud_reported = any(w in msg_lower for w in ["never placed", "fraud", "unauthorized", "didn't order"])

#         overdue_refund = False
#         rrn_to_share = ""
#         if self.order_data and ("refund" in msg_lower or "रिफ़ंड" in msg_lower):
#             initiated_on = self.order_data.get("return_refund_initiated_on") or self.order_data.get("cancellation_refund_initiated_on")
#             rrn_to_share = self.order_data.get("return_rrn") or self.order_data.get("cancellation_rrn") or ""
#             if initiated_on and initiated_on < "2026-10-10":
#                 overdue_refund = True

#         if human_requested or repeat_contact or high_value_damage or fraud_reported or overdue_refund:
#             reason = ("human_requested" if human_requested else "repeat_contact" if repeat_contact else
#                       "overdue_refund" if overdue_refund else "high_value_damage" if high_value_damage else "fraud_reported")
#             ticket_id = self._create_ticket(reason, message)
#             if ticket_id:
#                 extra_rrn = f" Here is your refund reference number (RRN): {rrn_to_share}." if rrn_to_share else ""
#                 reply = (f"I understand your concern.{extra_rrn} I have created a support ticket ({ticket_id}) "
#                          "and escalated your case to our Priority Resolution team / human colleague who will assist you shortly.")
#                 return self._finish(reply, first_turn)

#         # VERIFIED ORDER INQUIRIES
#         if self.verified and self.order_data:
#             return self._finish(self._answer_from_order(message), False)

#         # GENERAL POLICY / RAG GROUNDED QA
#         rag_res = answer_with_rag(message)
#         self.last_chunks = list(rag_res.get("retrieved_chunks", []))
#         self.last_sources = list(rag_res.get("used_section_ids", []))
#         reply = rag_res["response"]
#         if rag_res.get("escalate"):
#             ticket_id = self._create_ticket("high_value_damage_or_fraud", message)
#             if ticket_id:
#                 reply = reply.rstrip() + f"\nYour ticket number is {ticket_id}."
#         return self._finish(reply, first_turn)



#########################################################################################################################
# """Step 3: Multi-turn Conversational Support Agent for ZentroMart.

# Implements context memory, caller verification, policy enforcement,
# mock tool integration (lookup_order, create_ticket), and human handovers.
# """
# import json
# import re
# import sys
# from typing import Dict, List, Optional, Any

# from .config import DATASET_ROOT, REFERENCE_DATE
# from .rag import answer_with_rag, get_retriever
# from .llm import generate_text

# # Add tools directory to path to import synthetic tools
# sys.path.insert(0, str(DATASET_ROOT / "tools"))
# try:
#     from tools import lookup_order, create_ticket
# except ImportError:
#     def lookup_order(order_id: str, verification_value: str = None) -> dict:
#         return {"verification_required": True}
#     def create_ticket(summary: str, order_id: str = None, reason: str = None, intent: str = None) -> dict:
#         return {"created": True, "ticket_id": "TKT_MOCK"}


# AGENT_CONV_SYSTEM_PROMPT = (
#     "You are the customer support AI assistant for ZentroMart, an Indian online store "
#     "selling groceries and electronics. Today is 20 October 2026.\n\n"
#     "RULES:\n"
#     "1. Never greet or re-introduce yourself (no 'Hello', 'Namaste', 'I am your AI assistant'). Jump straight to the answer.\n"
#     "2. When VERIFIED ORDER DATA is provided the caller is already verified. Never ask for identity details again.\n"
#     "3. Use ONLY the verified order data and the policy context. Never invent dates, amounts or policies. "
#     "If neither covers the question, say you do not have that information in store policies and offer a human colleague.\n"
#     "4. Delivery: state promised_date; if it is already past and the order is not delivered, apologize politely. "
#     "For 'when was it shipped' use shipped_on; for delivered use delivered_on. State exact dates.\n"
#     "5. Returns: check delivered_on and the return window (electronics 7 days, fashion 15 days, BUT orders placed 1 to 15 October "
#     "festive sale get 30 days). State the exact return deadline date. ZentroMart Plus members have free returns; non-Plus members pay Rs 49 pickup.\n"
#     "6. Refunds: if the return is picked up, say quality check (QC) is pending. If the refund is overdue beyond the policy timeline, give the RRN.\n"
#     "7. Cancellation: possible only before the order ships. If shipped_on is set or the status is shipped, out for delivery or delivered, "
#     "politely decline: the order can no longer be cancelled. Then explain the return option and state the return window in days from the policy context.\n"
#     "8. Compensation, voucher or goodwill requests: apologize first, say you cannot grant vouchers or cash compensation yourself, "
#     "and state only what policy provides (for example the express fee credit for late Express orders). Never promise or add any credit.\n"
#     "9. NEVER say or imply that you created a ticket or escalated, unless the context contains 'TICKET RAISED: <id>'. Tickets are created by the system, not by you.\n"
#     "10. Write dates the way you would say them aloud, for example 15 October 2026, never 2026-10-15. "
#     "Answer only what the customer asked: do not bring up cancellation, returns or refunds unless they did.\n"
#     "11. Reply in the customer's language (English, Hindi or Hinglish). Be concise and spoken-friendly. "
#     "Plain text only: no markdown, no asterisks, no bullet symbols."
# )

# _MONTH_FIX = re.compile(r"\*+|^#+\s*", re.M)
# _LEADING_INTRO = re.compile(
#     r"^\s*(?:(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]*\s*)?"
#     r"(?:(?:i am|i'm|this is)\s+(?:your|the)\s+zentromart\s+ai(?:\s+customer\s+support)?\s+assistant|"
#     r"i am your ai assistant for zentromart)[.,!]?\s*",
#     re.I,
# )
# _LEADING_GREET = re.compile(r"^\s*(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]+\s*", re.I)

# # Words that mean the customer asked something specific (not just "I need help")
# _TOPIC_WORDS = [
#     "return", "refund", "cancel", "warranty", "deliver", "track", "where", "status", "damage", "defect",
#     "policy", "coupon", "price", "kab", "kahan", "wapas", "paisa", "replace", "exchange", "broken", "crack",
#     "late", "voucher", "compensation", "shipping", "ship", "payment", "upi", "card", "invoice", "gst",
#     "when", "how", "what", "can i", "do you", "kya", "kaise", "kitne", "?", "never placed", "fraud",
# ]


# def _is_generic_help(message: str) -> bool:
#     """True for openers like 'Hello, I need help with an order' that carry no specific question."""
#     m = message.lower()
#     if len(m.split()) > 14:
#         return False
#     if any(w in m for w in _TOPIC_WORDS):
#         return False
#     return True


# _MONTHS = ["January", "February", "March", "April", "May", "June", "July",
#            "August", "September", "October", "November", "December"]


# def _spoken_dates(text: str) -> str:
#     """2026-10-15 -> 15 October 2026 (also for timestamps like 2026-10-05T08:05)."""
#     def fix(m):
#         y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
#         return f"{d} {_MONTHS[mo - 1]} {y}" if 1 <= mo <= 12 else m.group(0)
#     return re.sub(r"\b(20\d{2})-(\d{2})-(\d{2})(?:T\d{2}:\d{2}(?::\d{2})?)?\b", fix, text)


# def _clean_reply(text: str, first_turn: bool) -> str:
#     text = _spoken_dates(text)
#     text = text.replace("**", "").replace("__", "")
#     text = re.sub(r"^\s*[*#]+\s*", "", text, flags=re.M)
#     if not first_turn:
#         for _ in range(3):
#             new = _LEADING_INTRO.sub("", text, count=1)
#             new = _LEADING_GREET.sub("", new, count=1)
#             if new == text:
#                 break
#             text = new
#     return text.strip()


# class SupportAgent:
#     """Conversational Customer Support Agent for ZentroMart."""

#     def __init__(self, conversation_id: str = "conv_default"):
#         self.conversation_id = conversation_id
#         self.history: List[Dict[str, str]] = []
#         self.order_id: Optional[str] = None
#         self.verified: bool = False
#         self.order_data: Optional[Dict[str, Any]] = None
#         self.verification_attempts: int = 0
#         self.escalated: bool = False
#         self.last_ticket_id: Optional[str] = None
#         # Evidence for the UI and run.py logs (reset on every turn)
#         self.last_chunks: List[str] = []   # section ids retrieved this turn
#         self.last_sources: List[str] = []  # section ids the answer cited

#     # ------------------------------------------------------------------ helpers
#     def _extract_digits(self, text: str) -> str:
#         """Extract all consecutive or spaced digits."""
#         return "".join(ch for ch in text if "0" <= ch <= "9")

#     def _extract_order_id(self, text: str) -> Optional[str]:
#         """8-digit order id, either '8978 2837' / '89782837' or digits spoken one by one."""
#         m = re.search(r"\b(\d{4})[\s-]?(\d{4})\b", text)
#         if m:
#             return m.group(1) + m.group(2)
#         digits = self._extract_digits(text)
#         return digits if len(digits) == 8 else None

#     def _is_turn_1(self) -> bool:
#         return len(self.history) <= 1

#     def _finish(self, reply: str, first_turn: bool) -> str:
#         reply = _clean_reply(reply, first_turn)
#         self.history.append({"role": "assistant", "content": reply})
#         return reply

#     def _create_ticket(self, reason: str, message: str) -> Optional[str]:
#         summary = (
#             f"Escalation required: Order {self.order_id or 'N/A'}. Reason: {reason}. "
#             f"Customer issue: {message}. Handing over to Priority Resolution team."
#         )
#         res = create_ticket(summary=summary, order_id=self.order_id, reason=reason)
#         if res.get("created"):
#             self.last_ticket_id = res.get("ticket_id")
#             self.escalated = True
#             return self.last_ticket_id
#         return None

#     def _answer_from_order(self, message: str, just_verified: bool = False) -> str:
#         """LLM answer grounded in the verified order record + retrieved policy sections."""
#         customer_msgs = [h["content"] for h in self.history if h["role"] == "customer"]
#         if just_verified:
#             earlier0 = [m for m in customer_msgs[:-1] if not re.fullmatch(r"[\d\s\-.]*", m.strip())]
#             if not any(not _is_generic_help(m) for m in earlier0):
#                 self.last_chunks, self.last_sources = [], []
#                 name0 = self.order_data.get("customer_first_name", "")
#                 return (f"Thank you, {name0}, you are verified. "
#                         f"How can I help you with order {self.order_id} today?")
#         retrieval_query = " ".join(customer_msgs[:-1])[:300] + " " + message if just_verified else message
#         chunks = get_retriever().retrieve(retrieval_query.strip(), top_k=3)
#         self.last_chunks = [c["section_id"] for c in chunks]
#         self.last_sources = list(self.last_chunks)
#         kb_context = "\n".join(f"[{c['section_id']}] {c['text']}" for c in chunks)
#         order_info = json.dumps(self.order_data, ensure_ascii=False, default=str, indent=1)
#         ticket_line = f"TICKET RAISED: {self.last_ticket_id}" if self.last_ticket_id else "No ticket has been raised."
#         convo = "\n".join(f"{h['role']}: {h['content']}" for h in self.history[-8:])

#         if just_verified:
#             earlier = [m for m in customer_msgs[:-1] if not re.fullmatch(r"[\d\s\-.]*", m.strip())]
#             has_question = any(not _is_generic_help(m) for m in earlier)
#             first_name = self.order_data.get("customer_first_name", "")
#             if not has_question:
#                 # Nothing was asked yet (only the order number and the verification digits): do not guess a question
#                 self.last_chunks, self.last_sources = [], []
#                 return (f"Thank you, {first_name}, you are verified. "
#                         f"How can I help you with order {self.order_id} today?")
#             task = (
#                 f"The caller has JUST been verified. Start with: 'Thank you, {first_name}, you are verified.' "
#                 "Then look at the conversation: if the customer already asked a specific question (for example where is my order, "
#                 "return, refund, cancellation), answer it now using the order data. If they only asked for general help, "
#                 "ask what they would like to know about the order. Do not greet."
#             )
#         else:
#             task = "Answer the customer's latest message directly and concisely."

#         prompt = (
#             "CALLER VERIFICATION STATUS: ALREADY FULLY VERIFIED.\n\n"
#             f"VERIFIED ORDER DATA (JSON):\n{order_info}\n\n"
#             f"COMPANY POLICY CONTEXT:\n{kb_context}\n\n"
#             f"SYSTEM STATUS: {ticket_line}\n\n"
#             f"CONVERSATION SO FAR:\n{convo}\n\n"
#             f"CUSTOMER LATEST MESSAGE:\n{message}\n\n{task}"
#         )
#         return generate_text(prompt, system_instruction=AGENT_CONV_SYSTEM_PROMPT, temperature=0.0)

#     # ------------------------------------------------------------------ main
#     def respond(self, message: str) -> str:
#         """Process incoming customer message and return agent's response."""
#         self.history.append({"role": "customer", "content": message})
#         self.last_chunks, self.last_sources = [], []
#         first_turn = self._is_turn_1()
#         msg_lower = message.lower()
#         extracted_nums = self._extract_digits(message)

#         # TURN 1: generic opener -> greet and ask for order id.
#         # A specific first question (e.g. "What is the return window for electronics?") is answered below instead.
#         if first_turn and not self.order_id and not self._extract_order_id(message) and _is_generic_help(message):
#             return self._finish(
#                 "Hello! I am your ZentroMart AI assistant. I'm here to help you. "
#                 "Could you please share your 8-digit order ID so I can assist you?", True)

#         # TURN 2: order id provided -> identity verification gate
#         if not self.order_id:
#             oid = self._extract_order_id(message)
#             if oid:
#                 self.order_id = oid
#                 lookup_order(self.order_id)  # unverified lookup call
#                 return self._finish(
#                     f"Thank you. I have located order {self.order_id}. For your security, "
#                     "could you please verify your identity by providing either the last 4 digits "
#                     "of your registered phone number OR your 6-digit delivery pincode?", first_turn)

#         # TURN 3: verification value provided
#         if self.order_id and not self.verified and len(extracted_nums) in (4, 6):
#             result = lookup_order(self.order_id, verification_value=extracted_nums)
#             if result.get("verified"):
#                 self.verified = True
#                 self.order_data = result
#                 first_name = result.get("customer_first_name", "Valued Customer")
#                 try:
#                     reply = self._answer_from_order(message, just_verified=True)
#                 except Exception:
#                     reply = (f"Thank you, {first_name}! Verification successful. "
#                              f"How can I help you with order {self.order_id} today?")
#                 return self._finish(reply, False)
#             self.verification_attempts += 1
#             if self.verification_attempts >= 2:
#                 reply = ("I'm sorry, verification has failed. For security reasons, "
#                          "I cannot share details for this order. Please reach out to our team from your registered phone.")
#             else:
#                 reply = "The verification details did not match. Please re-check and provide your phone's last 4 digits or pincode."
#             return self._finish(reply, first_turn)

#         # ESCALATION TRIGGERS (ESC-1..ESC-4) - decided in code, never by the LLM
#         human_requested = any(w in msg_lower for w in [
#             "human", "person", "agent", "colleague", "executive", "representative",
#             "इंसान", "सहयोगी", "baat kar sakti", "baat karni hai"])

#         repeat_contact = (not self.escalated) and (
#             "third time" in msg_lower or "teesri baar" in msg_lower or
#             bool(self.order_data and int(self.order_data.get("contacts_last_7_days") or 0) >= 2))

#         high_value_damage = False
#         if self.order_data and any(w in msg_lower for w in ["damage", "defective", "kharab", "replacement", "crack", "broken"]):
#             for it in self.order_data.get("items", []):
#                 if int(float(it.get("unit_price_inr") or 0)) >= 10000:
#                     high_value_damage = True

#         fraud_reported = any(w in msg_lower for w in ["never placed", "fraud", "unauthorized", "didn't order"])

#         overdue_refund = False
#         rrn_to_share = ""
#         if self.order_data and ("refund" in msg_lower or "रिफ़ंड" in msg_lower):
#             initiated_on = self.order_data.get("return_refund_initiated_on") or self.order_data.get("cancellation_refund_initiated_on")
#             rrn_to_share = self.order_data.get("return_rrn") or self.order_data.get("cancellation_rrn") or ""
#             if initiated_on and initiated_on < "2026-10-10":
#                 overdue_refund = True

#         if human_requested or repeat_contact or high_value_damage or fraud_reported or overdue_refund:
#             reason = ("human_requested" if human_requested else "repeat_contact" if repeat_contact else
#                       "overdue_refund" if overdue_refund else "high_value_damage" if high_value_damage else "fraud_reported")
#             ticket_id = self._create_ticket(reason, message)
#             if ticket_id:
#                 extra_rrn = f" Here is your refund reference number (RRN): {rrn_to_share}." if rrn_to_share else ""
#                 reply = (f"I understand your concern.{extra_rrn} I have created a support ticket ({ticket_id}) "
#                          "and escalated your case to our Priority Resolution team / human colleague who will assist you shortly.")
#                 return self._finish(reply, first_turn)

#         # VERIFIED ORDER INQUIRIES
#         if self.verified and self.order_data:
#             return self._finish(self._answer_from_order(message), False)

#         # GENERAL POLICY / RAG GROUNDED QA
#         rag_res = answer_with_rag(message)
#         self.last_chunks = list(rag_res.get("retrieved_chunks", []))
#         self.last_sources = list(rag_res.get("used_section_ids", []))
#         reply = rag_res["response"]
#         if rag_res.get("escalate"):
#             ticket_id = self._create_ticket("high_value_damage_or_fraud", message)
#             if ticket_id:
#                 reply = reply.rstrip() + f"\nYour ticket number is {ticket_id}."
#         return self._finish(reply, first_turn)


"""Step 3: Multi-turn Conversational Support Agent for ZentroMart.

Implements context memory, caller verification, policy enforcement,
mock tool integration (lookup_order, create_ticket), and human handovers.
"""
import json
import re
import sys
from typing import Dict, List, Optional, Any

from .config import DATASET_ROOT, REFERENCE_DATE
from .rag import answer_with_rag, get_retriever
from .llm import generate_text

# Add tools directory to path to import synthetic tools
sys.path.insert(0, str(DATASET_ROOT / "tools"))
try:
    from tools import lookup_order, create_ticket
except ImportError:
    def lookup_order(order_id: str, verification_value: str = None) -> dict:
        return {"verification_required": True}
    def create_ticket(summary: str, order_id: str = None, reason: str = None, intent: str = None) -> dict:
        return {"created": True, "ticket_id": "TKT_MOCK"}


AGENT_CONV_SYSTEM_PROMPT = (
    "You are the customer support AI assistant for ZentroMart, an Indian online store "
    "selling groceries and electronics. Today is 20 October 2026.\n\n"
    "RULES:\n"
    "1. Never greet or re-introduce yourself (no 'Hello', 'Namaste', 'I am your AI assistant'). Jump straight to the answer.\n"
    "2. When VERIFIED ORDER DATA is provided the caller is already verified. Never ask for identity details again.\n"
    "3. Use ONLY the verified order data and the policy context. Never invent dates, amounts or policies. "
    "If neither covers the question, say you do not have that information in store policies and offer a human colleague.\n"
    "4. Delivery: state promised_date; if it is already past and the order is not delivered, apologize politely. "
    "For 'when was it shipped' use shipped_on; for delivered use delivered_on. State exact dates.\n"
    "5. Returns: check delivered_on and the return window (electronics 7 days, fashion 15 days, BUT orders placed 1 to 15 October "
    "festive sale get 30 days). State the exact return deadline date. ZentroMart Plus members have free returns; non-Plus members pay Rs 49 pickup.\n"
    "6. Refunds: if the return is picked up, say quality check (QC) is pending. If the refund is overdue beyond the policy timeline, give the RRN.\n"
    "7. Cancellation: possible only before the order ships. If shipped_on is set or the status is shipped, out for delivery or delivered, "
    "politely decline: the order can no longer be cancelled. Then explain the return option and state the return window in days from the policy context.\n"
    "8. Compensation, voucher or goodwill requests: politely say that policy does not allow it and you cannot grant it. "
    "Never promise or add any credit. (The system raises the ticket and hands over to a human; do not claim a ticket yourself.)\n"
    "9. NEVER say or imply that you created a ticket or escalated, unless the context contains 'TICKET RAISED: <id>'. Tickets are created by the system, not by you.\n"
    "10. Write dates the way you would say them aloud, for example 15 October 2026, never 2026-10-15. "
    "Answer only what the customer asked: do not bring up cancellation, returns or refunds unless they did.\n"
    "11. Reply in the customer's language (English, Hindi or Hinglish). Be concise and spoken-friendly. "
    "Plain text only: no markdown, no asterisks, no bullet symbols."
)

_MONTH_FIX = re.compile(r"\*+|^#+\s*", re.M)
_LEADING_INTRO = re.compile(
    r"^\s*(?:(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]*\s*)?"
    r"(?:(?:i am|i'm|this is)\s+(?:your|the)\s+zentromart\s+ai(?:\s+customer\s+support)?\s+assistant|"
    r"i am your ai assistant for zentromart)[.,!]?\s*",
    re.I,
)
_LEADING_GREET = re.compile(r"^\s*(?:hello|hi|hey|namaste|namaskar|नमस्ते)\s*[!,.:-]+\s*", re.I)

# Words that mean the customer asked something specific (not just "I need help")
_TOPIC_WORDS = [
    "return", "refund", "cancel", "warranty", "deliver", "track", "where", "status", "damage", "defect",
    "policy", "coupon", "price", "kab", "kahan", "wapas", "paisa", "replace", "exchange", "broken", "crack",
    "late", "voucher", "compensation", "shipping", "ship", "payment", "upi", "card", "invoice", "gst",
    "when", "how", "what", "can i", "do you", "kya", "kaise", "kitne", "?", "never placed", "fraud",
]


_COMP_WORDS = ["compensation", "compensate", "voucher", "goodwill", "muavza", "मुआवज़ा", "मुआवजा"]
_ORDER_SPECIFIC = re.compile(
    r"\b(my|mera|mere|meri)\s+(order|parcel|package|delivery|refund|return|item|product)\b|"
    r"\border\s+(hasn't|has not|hasnt|nahi|not)\b", re.I)


def _is_generic_help(message: str) -> bool:
    """True for openers like 'Hello, I need help with an order' that carry no specific question."""
    m = message.lower()
    if len(m.split()) > 14:
        return False
    if any(w in m for w in _TOPIC_WORDS):
        return False
    return True


_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December"]


def _spoken_dates(text: str) -> str:
    """2026-10-15 -> 15 October 2026 (also for timestamps like 2026-10-05T08:05)."""
    def fix(m):
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{d} {_MONTHS[mo - 1]} {y}" if 1 <= mo <= 12 else m.group(0)
    return re.sub(r"\b(20\d{2})-(\d{2})-(\d{2})(?:T\d{2}:\d{2}(?::\d{2})?)?\b", fix, text)


def _clean_reply(text: str, first_turn: bool) -> str:
    text = _spoken_dates(text)
    text = text.replace("**", "").replace("__", "")
    text = re.sub(r"^\s*[*#]+\s*", "", text, flags=re.M)
    if not first_turn:
        for _ in range(3):
            new = _LEADING_INTRO.sub("", text, count=1)
            new = _LEADING_GREET.sub("", new, count=1)
            if new == text:
                break
            text = new
    return text.strip()


class SupportAgent:
    """Conversational Customer Support Agent for ZentroMart."""

    def __init__(self, conversation_id: str = "conv_default"):
        self.conversation_id = conversation_id
        self.history: List[Dict[str, str]] = []
        self.order_id: Optional[str] = None
        self.verified: bool = False
        self.order_data: Optional[Dict[str, Any]] = None
        self.verification_attempts: int = 0
        self.escalated: bool = False
        self.last_ticket_id: Optional[str] = None
        self.compensation_ticket: Optional[str] = None  # ticket raised for a compensation request
        # Evidence for the UI and run.py logs (reset on every turn)
        self.last_chunks: List[str] = []   # section ids retrieved this turn
        self.last_sources: List[str] = []  # section ids the answer cited

    # ------------------------------------------------------------------ helpers
    def _extract_digits(self, text: str) -> str:
        """Extract numeric digits, including spoken digit sequences."""
        import re

        digit_words = {
            "zero": "0",
            "oh": "0",
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
        }

        # Match numeric digits or individual spoken digit words
        tokens = re.findall(r"\b(?:zero|oh|one|two|three|four|five|six|seven|eight|nine|\d+)\b",
                        text.lower())

        return "".join(digit_words.get(token, token) for token in tokens)

    def _extract_order_id(self, text: str) -> Optional[str]:
        """8-digit order id, either '8978 2837' / '89782837' or digits spoken one by one."""
        m = re.search(r"\b(\d{4})[\s-]?(\d{4})\b", text)
        if m:
            return m.group(1) + m.group(2)
        digits = self._extract_digits(text)
        return digits if len(digits) == 8 else None

    def _is_turn_1(self) -> bool:
        return len(self.history) <= 1

    def _finish(self, reply: str, first_turn: bool) -> str:
        reply = _clean_reply(reply, first_turn)
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def _create_ticket(self, reason: str, message: str) -> Optional[str]:
        summary = (
            f"Escalation required: Order {self.order_id or 'N/A'}. Reason: {reason}. "
            f"Customer issue: {message}. Handing over to Priority Resolution team."
        )
        res = create_ticket(summary=summary, order_id=self.order_id, reason=reason)
        if res.get("created"):
            self.last_ticket_id = res.get("ticket_id")
            self.escalated = True
            return self.last_ticket_id
        return None

    def _answer_from_order(self, message: str, just_verified: bool = False) -> str:
        """LLM answer grounded in the verified order record + retrieved policy sections."""
        customer_msgs = [h["content"] for h in self.history if h["role"] == "customer"]
        if just_verified:
            earlier0 = [m for m in customer_msgs[:-1] if not re.fullmatch(r"[\d\s\-.]*", m.strip())]
            if not any(not _is_generic_help(m) for m in earlier0):
                self.last_chunks, self.last_sources = [], []
                name0 = self.order_data.get("customer_first_name", "")
                return (f"Thank you, {name0}, you are verified. "
                        f"How can I help you with order {self.order_id} today?")
        retrieval_query = " ".join(customer_msgs[:-1])[:300] + " " + message if just_verified else message
        chunks = get_retriever().retrieve(retrieval_query.strip(), top_k=3)
        self.last_chunks = [c["section_id"] for c in chunks]
        self.last_sources = list(self.last_chunks)
        kb_context = "\n".join(f"[{c['section_id']}] {c['text']}" for c in chunks)
        order_info = json.dumps(self.order_data, ensure_ascii=False, default=str, indent=1)
        ticket_line = f"TICKET RAISED: {self.last_ticket_id}" if self.last_ticket_id else "No ticket has been raised."
        convo = "\n".join(f"{h['role']}: {h['content']}" for h in self.history[-8:])

        if just_verified:
            earlier = [m for m in customer_msgs[:-1] if not re.fullmatch(r"[\d\s\-.]*", m.strip())]
            has_question = any(not _is_generic_help(m) for m in earlier)
            first_name = self.order_data.get("customer_first_name", "")
            if not has_question:
                # Nothing was asked yet (only the order number and the verification digits): do not guess a question
                self.last_chunks, self.last_sources = [], []
                return (f"Thank you, {first_name}, you are verified. "
                        f"How can I help you with order {self.order_id} today?")
            task = (
                f"The caller has JUST been verified. Start with: 'Thank you, {first_name}, you are verified.' "
                "Then look at the conversation: if the customer already asked a specific question (for example where is my order, "
                "return, refund, cancellation), answer it now using the order data. If they only asked for general help, "
                "ask what they would like to know about the order. Do not greet."
            )
        else:
            task = "Answer the customer's latest message directly and concisely."

        prompt = (
            "CALLER VERIFICATION STATUS: ALREADY FULLY VERIFIED.\n\n"
            f"VERIFIED ORDER DATA (JSON):\n{order_info}\n\n"
            f"COMPANY POLICY CONTEXT:\n{kb_context}\n\n"
            f"SYSTEM STATUS: {ticket_line}\n\n"
            f"CONVERSATION SO FAR:\n{convo}\n\n"
            f"CUSTOMER LATEST MESSAGE:\n{message}\n\n{task}"
        )
        return generate_text(prompt, system_instruction=AGENT_CONV_SYSTEM_PROMPT, temperature=0.0)

    # ------------------------------------------------------------------ main
    def respond(self, message: str) -> str:
        """Process incoming customer message and return agent's response."""
        self.history.append({"role": "customer", "content": message})
        self.last_chunks, self.last_sources = [], []
        first_turn = self._is_turn_1()
        msg_lower = message.lower()
        extracted_nums = self._extract_digits(message)

        # TURN 1: generic opener -> greet and ask for order id.
        # A specific first question (e.g. "What is the return window for electronics?") is answered below instead.
        if (first_turn and not self.order_id and not self._extract_order_id(message)
                and (_is_generic_help(message) or _ORDER_SPECIFIC.search(message))
                and not any(w in msg_lower for w in _COMP_WORDS)):
            return self._finish(
                "Hello! I am your ZentroMart AI assistant. I'm here to help you. "
                "Could you please share your 8-digit order ID so I can assist you?", True)

        # COMPENSATION / VOUCHER REQUEST: policy does not allow it -> say so politely, raise a ticket, hand over to a human
        if any(w in msg_lower for w in _COMP_WORDS):
            if self.compensation_ticket:
                return self._finish(
                    f"I understand, and I'm sorry for the trouble. Policy does not allow me to grant compensation. "
                    f"Your request is already with a human colleague under ticket {self.compensation_ticket}, "
                    "and they will assist you shortly.", first_turn)
            summary = (f"Customer requested compensation (\"{message}\") on order {self.order_id or 'N/A'}"
                       f"{' (caller verified)' if self.verified else ' (caller not verified)'}. "
                       "Policy does not allow agent-granted compensation. Handed over to a human colleague.")
            res = create_ticket(summary=summary, order_id=self.order_id, reason="compensation_request")
            if res.get("created"):
                self.last_ticket_id = self.compensation_ticket = res.get("ticket_id")
                self.escalated = True
                return self._finish(
                    "I'm sorry for the trouble, but our policy does not allow me to grant compensation or vouchers. "
                    f"I have created a support ticket ({self.last_ticket_id}) with a short summary and handed your request over "
                    "to a human colleague, who will assist you shortly.", first_turn)

        # TURN 2: order id provided -> identity verification gate
        if not self.order_id:
            oid = self._extract_order_id(message)
            if oid:
                self.order_id = oid
                lookup_order(self.order_id)  # unverified lookup call
                return self._finish(
                    f"Thank you. I have located order {self.order_id}. For your security, "
                    "could you please verify your identity by providing either the last 4 digits "
                    "of your registered phone number OR your 6-digit delivery pincode?", first_turn)

        # TURN 3: verification value provided
        if self.order_id and not self.verified and len(extracted_nums) in (4, 6):
            result = lookup_order(self.order_id, verification_value=extracted_nums)
            if result.get("verified"):
                self.verified = True
                self.order_data = result
                first_name = result.get("customer_first_name", "Valued Customer")
                try:
                    reply = self._answer_from_order(message, just_verified=True)
                except Exception:
                    reply = (f"Thank you, {first_name}! Verification successful. "
                             f"How can I help you with order {self.order_id} today?")
                return self._finish(reply, False)
            self.verification_attempts += 1
            if self.verification_attempts >= 2:
                reply = ("I'm sorry, verification has failed. For security reasons, "
                         "I cannot share details for this order. Please reach out to our team from your registered phone.")
            else:
                reply = "The verification details did not match. Please re-check and provide your phone's last 4 digits or pincode."
            return self._finish(reply, first_turn)

        # ESCALATION TRIGGERS (ESC-1..ESC-4) - decided in code, never by the LLM
        human_requested = any(w in msg_lower for w in [
            "human", "person", "agent", "colleague", "executive", "representative",
            "इंसान", "सहयोगी", "baat kar sakti", "baat karni hai"])

        repeat_contact = (not self.escalated) and (
            "third time" in msg_lower or "teesri baar" in msg_lower or
            bool(self.order_data and int(self.order_data.get("contacts_last_7_days") or 0) >= 2))

        high_value_damage = False
        if self.order_data and any(w in msg_lower for w in ["damage", "defective", "kharab", "replacement", "crack", "broken"]):
            for it in self.order_data.get("items", []):
                if int(float(it.get("unit_price_inr") or 0)) >= 10000:
                    high_value_damage = True

        fraud_reported = any(w in msg_lower for w in ["never placed", "fraud", "unauthorized", "didn't order"])

        overdue_refund = False
        rrn_to_share = ""
        if self.order_data and ("refund" in msg_lower or "रिफ़ंड" in msg_lower):
            initiated_on = self.order_data.get("return_refund_initiated_on") or self.order_data.get("cancellation_refund_initiated_on")
            rrn_to_share = self.order_data.get("return_rrn") or self.order_data.get("cancellation_rrn") or ""
            if initiated_on and initiated_on < "2026-10-10":
                overdue_refund = True

        if human_requested or repeat_contact or high_value_damage or fraud_reported or overdue_refund:
            reason = ("human_requested" if human_requested else "repeat_contact" if repeat_contact else
                      "overdue_refund" if overdue_refund else "high_value_damage" if high_value_damage else "fraud_reported")
            ticket_id = self._create_ticket(reason, message)
            if ticket_id:
                extra_rrn = f" Here is your refund reference number (RRN): {rrn_to_share}." if rrn_to_share else ""
                reply = (f"I understand your concern.{extra_rrn} I have created a support ticket ({ticket_id}) "
                         "and escalated your case to our Priority Resolution team / human colleague who will assist you shortly.")
                return self._finish(reply, first_turn)

        # VERIFIED ORDER INQUIRIES
        if self.verified and self.order_data:
            return self._finish(self._answer_from_order(message), False)

        # GENERAL POLICY / RAG GROUNDED QA
        rag_res = answer_with_rag(message)
        self.last_chunks = list(rag_res.get("retrieved_chunks", []))
        self.last_sources = list(rag_res.get("used_section_ids", []))
        reply = rag_res["response"]
        if rag_res.get("escalate"):
            ticket_id = self._create_ticket("high_value_damage_or_fraud", message)
            if ticket_id:
                reply = reply.rstrip() + f"\nYour ticket number is {ticket_id}."
        return self._finish(reply, first_turn)