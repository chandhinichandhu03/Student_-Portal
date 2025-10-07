import os
from typing import List, Dict

try:
	import google.generativeai as genai
except Exception:  # pragma: no cover
	genai = None


class GeminiClient:
	def __init__(self, api_key: str | None = None):
		self.api_key = api_key or os.getenv("GEMINI_API_KEY")
		self.enabled = bool(self.api_key and genai)
		if self.enabled:
			genai.configure(api_key=self.api_key)
			self.model = genai.GenerativeModel("gemini-2.5-flash")
		else:
			self.model = None

	def _sanitize(self, s: str | None) -> str:
		if not s:
			return ""
		text = str(s)
		# remove markdown emphasis and code fences artifacts
		text = text.replace("**", "").replace("*", "")
		text = text.replace("```json", "").replace("```", "")
		# trim bullets/prefixes commonly added in lists
		text = text.strip().lstrip("- ").lstrip("ABCD). ")
		return text

	def _extract_json(self, text: str) -> str:
		if not text:
			return "{}"
		# Strip Markdown code fences if present
		text = text.strip()
		if text.startswith("```"):
			# remove starting fence and possible language
			first_newline = text.find("\n")
			if first_newline != -1:
				text = text[first_newline+1:]
			# remove ending fence
			end = text.rfind("```")
			if end != -1:
				text = text[:end]
		# Try to isolate the outermost JSON object
		start = text.find("{")
		end = text.rfind("}")
		if start != -1 and end != -1 and end > start:
			return text[start:end+1]
		return text

	def _response_text(self, resp) -> str:
		# Prefer direct .text when available
		text = getattr(resp, "text", None)
		if text:
			return text
		# Try candidates -> content -> parts
		try:
			cands = getattr(resp, "candidates", None) or []
			for c in cands:
				content = getattr(c, "content", None)
				if not content:
					continue
				parts = getattr(content, "parts", None) or []
				for p in parts:
					pt = getattr(p, "text", None)
					if pt:
						return pt
		except Exception:
			pass
		return ""

	def generate_mcqs(self, topic: str, num_questions: int = 5) -> List[Dict]:
		# Always try AI first if key is present, even if genai import failed
		if self.api_key:
			try:
				prompt = (
					f"Generate {num_questions} multiple-choice questions on '{topic}'. "
					"Return ONLY raw JSON, no prose, no markdown fences. "
					"The JSON shape: {\"questions\":[{\"question\":str,\"options\":[str,str,str,str],\"correct\":str,\"difficulty\":str}]}."
				)
				resp = self.model.generate_content(prompt)
				text_raw = self._response_text(resp) or "{}"
				print(f"DEBUG: Raw Gemini response: {text_raw[:200]}...")  # Debug log
				text = self._extract_json(text_raw)
				print(f"DEBUG: Extracted JSON: {text[:200]}...")  # Debug log
				import json
				data = json.loads(text)
				questions = data.get("questions", [])
				parsed: List[Dict] = []
				for q in questions:
					opts_raw = q.get("options", [])
					# Normalize options to 4 strings
					opts = [self._sanitize(o) for o in opts_raw if o]
					if len(opts) < 4:
						continue
					opts = opts[:4]
					question_text = self._sanitize(q.get("question", ""))
					if not question_text:
						continue
					correct = self._sanitize(q.get("correct", ""))
					# If correct not in options, default to first option
					if correct not in opts:
						correct = opts[0]
					parsed.append({
						"question": question_text,
						"options": opts,
						"correct": correct,
						"difficulty": self._sanitize(q.get("difficulty", "medium")) or "medium",
					})
				print(f"DEBUG: Parsed {len(parsed)} questions")  # Debug log
				if parsed:
					return parsed[:num_questions]
			except Exception as e:
				print(f"DEBUG: Gemini error: {e}")  # Debug log
		
		# Fallback mock only if no API key or all AI attempts failed
		items = []
		for i in range(num_questions):
			items.append({
				"question": f"Sample question {i+1} on {topic}?",
				"options": ["Option A", "Option B", "Option C", "Option D"],
				"correct": "Option A",
				"difficulty": "medium",
			})
		return items

