# ============================================
# FaultAI — GROQ CLIENT (PDF-Based RAG)
# Handles communication with Groq API
# (Llama 3.3 70B — multilingual support)
#
# This module:
#   1. Sends symptoms + PDF passages to Groq LLM
#   2. LLM generates fault diagnosis + solutions
#   3. Returns the AI-generated response
# ============================================

import requests
import json


class GrokClient:
    """
    Client for Groq API (Llama 3.3 70B).

    Sends user symptoms along with RAG-retrieved PDF passages
    to Groq's LLM, which generates intelligent fault diagnoses.
    Supports multilingual input/output including Tamil.
    """

    # ── Groq API Configuration ──
    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    MODEL = "llama-3.3-70b-versatile"    # Llama 3.3 70B on Groq (multilingual)

    def __init__(self, api_key=None):
        self.api_key = api_key
        if api_key:
            print(f"✅ Grok client initialized (key: {api_key[:8]}...)")
        else:
            print("⚠️ Grok client initialized WITHOUT API key (will use fallback)")

    def set_api_key(self, api_key):
        """Update the API key"""
        self.api_key = api_key

    def generate_solution(self, symptoms, rag_results):
        """
        Generate a diagnosis solution using Grok API.

        Args:
            symptoms (str):      User's symptom description
            rag_results (list):  Retrieved PDF passages from RAG engine

        Returns:
            dict: Contains 'diagnosis', 'solution_html', and 'fault_name'
        """

        # ── If no API key, use fallback response ──
        if not self.api_key:
            return self._fallback_response(rag_results)

        # ── Build context from RAG results ──
        rag_context = self._format_rag_context(rag_results)

        # ── Create the prompt for Groq LLM ──
        prompt = f"""You are FaultAI, an expert hydraulic systems fault diagnosis assistant.
You have access to the Vickers Industrial Hydraulics Manual as your knowledge base.

Based on the user's symptom description and the retrieved passages from the hydraulics manual,
provide a clear, structured diagnosis.

IMPORTANT: Respond in the SAME LANGUAGE the user used to describe their symptoms.
If the user wrote in Tamil, respond entirely in Tamil. If in English, respond in English.

USER SYMPTOMS:
{symptoms}

RETRIEVED PASSAGES FROM HYDRAULICS MANUAL:
{rag_context}

Based on these passages, provide:
1. **Fault Name**: A concise name for the diagnosed fault (e.g., "Pump cavitation", "Relief valve failure")
2. **Root Cause**: What is causing this issue based on the manual
3. **Step-by-step Repair Instructions**: Numbered list of specific, actionable repair steps
4. **Safety Warnings**: Any safety precautions from the manual
5. **Prevention Tips**: How to prevent this fault in the future

IMPORTANT: Base your diagnosis on the retrieved manual passages. Reference page numbers when possible.
Format your response as a clear numbered list. Be specific and actionable."""

        try:
            # ═══════════════════════════════════════
            # ► ACTUAL GROQ API CALL (Llama 3.3 70B)
            # ═══════════════════════════════════════
            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are FaultAI, an expert hydraulic systems fault diagnosis assistant. You use the Vickers Industrial Hydraulics Manual as your knowledge base. Provide clear, actionable solutions grounded in the manual content."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "temperature": 0.7,
                    "max_tokens": 1500
                },
                timeout=30
            )

            # ── Parse the response ──
            if response.status_code == 200:
                data = response.json()
                solution_text = data["choices"][0]["message"]["content"]

                # Try to extract a fault name from the response
                fault_name = self._extract_fault_name(solution_text)

                return {
                    "fault_name": fault_name,
                    "solution_html": self._format_as_html(solution_text),
                    "raw_text": solution_text
                }
            else:
                print(f"❌ Grok API error: {response.status_code} - {response.text}")
                return self._fallback_response(rag_results)

        except requests.exceptions.Timeout:
            print("❌ Grok API timeout")
            return self._fallback_response(rag_results)
        except Exception as e:
            print(f"❌ Grok API exception: {e}")
            return self._fallback_response(rag_results)

    def _format_rag_context(self, rag_results):
        """Format RAG-retrieved PDF passages into context string for Grok."""
        context = ""
        for i, passage in enumerate(rag_results, 1):
            page_info = f"Page {passage['page_start']}"
            if passage['page_start'] != passage['page_end']:
                page_info = f"Pages {passage['page_start']}-{passage['page_end']}"

            context += f"""
--- Passage {i} ({page_info}, Relevance: {passage.get('similarity_score', 'N/A')}%) ---
{passage['text'][:1500]}
"""
        return context

    def _extract_fault_name(self, text):
        """Try to extract a concise fault name from Grok's response."""
        lines = text.strip().split("\n")
        for line in lines:
            line_lower = line.lower().strip()
            # Look for lines like "Fault Name: ..." or "**Fault Name**: ..."
            if "fault name" in line_lower or "diagnosis" in line_lower:
                # Extract the value after the colon
                if ":" in line:
                    fault = line.split(":", 1)[1].strip()
                    # Clean markdown
                    fault = fault.replace("**", "").replace("*", "").strip()
                    if fault and len(fault) < 100:
                        return fault
        # Fallback: use first meaningful line
        for line in lines:
            cleaned = line.strip().lstrip("0123456789.-) #*").strip()
            if cleaned and len(cleaned) > 10 and len(cleaned) < 100:
                return cleaned
        return "Hydraulic System Fault"

    def _fallback_response(self, rag_results):
        """
        Generate a response WITHOUT calling Grok API.
        Uses only RAG-retrieved PDF passages.
        Used when: no API key, API error, or rate limit.
        """
        if not rag_results:
            return {
                "fault_name": "No matching fault found",
                "solution_html": "<p>No relevant passages found in the hydraulics manual. Try describing the symptoms differently.</p>",
                "raw_text": "No matching passages found."
            }

        # Build HTML from the top retrieved passages
        passages_html = ""
        for i, passage in enumerate(rag_results[:3], 1):
            page_info = f"Page {passage['page_start']}"
            if passage['page_start'] != passage['page_end']:
                page_info = f"Pages {passage['page_start']}-{passage['page_end']}"

            # Truncate for display
            display_text = passage['text'][:500]
            if len(passage['text']) > 500:
                display_text += "..."

            passages_html += f"""
            <li>
                <strong>Passage {i} ({page_info}):</strong>
                <p class="text-gray-300 mt-1">{display_text}</p>
            </li>
"""

        # Try to extract a fault name from the most relevant passage
        best_text = rag_results[0]["text"][:200].replace("\n", " ")

        return {
            "fault_name": "Hydraulic System Issue (RAG Retrieval)",
            "solution_html": f"""
            <p class="text-sm text-amber-400 mb-4">
                ⚠️ These are raw passages retrieved from the Vickers Hydraulics Manual.
                Add your xAI API key to get AI-analyzed diagnosis and step-by-step solutions.
            </p>
            <ol class="list-decimal pl-5 space-y-6 text-sm">
                {passages_html}
            </ol>
            <p class="text-xs text-gray-400 mt-6">
                📖 Source: Vickers Industrial Hydraulics Manual
            </p>""",
            "raw_text": best_text
        }

    def _format_as_html(self, text):
        """Convert Grok's plain text response to HTML."""
        lines = text.strip().split("\n")
        html = '<div class="space-y-3 text-sm">\n'
        in_list = False

        for line in lines:
            line = line.strip()
            if not line:
                if in_list:
                    html += "</ol>\n"
                    in_list = False
                continue

            # Check if it's a numbered item
            is_numbered = False
            for prefix_len in range(1, 4):
                if line[:prefix_len + 1].rstrip().rstrip(".").rstrip(")").isdigit():
                    is_numbered = True
                    break

            if is_numbered:
                if not in_list:
                    html += '<ol class="list-decimal pl-5 space-y-2">\n'
                    in_list = True
                cleaned = line.lstrip("0123456789.-) ").strip()
                # Bold text between **...**
                cleaned = self._markdown_to_html(cleaned)
                html += f"  <li>{cleaned}</li>\n"
            elif line.startswith("**") or line.startswith("#"):
                if in_list:
                    html += "</ol>\n"
                    in_list = False
                cleaned = line.lstrip("# ").replace("**", "").strip()
                html += f'<h4 class="font-semibold text-white mt-4 mb-1">{cleaned}</h4>\n'
            else:
                if in_list:
                    html += "</ol>\n"
                    in_list = False
                cleaned = self._markdown_to_html(line)
                html += f"<p>{cleaned}</p>\n"

        if in_list:
            html += "</ol>\n"
        html += "</div>"
        return html

    def _markdown_to_html(self, text):
        """Convert basic markdown bold/italic to HTML."""
        import re
        # **bold** → <strong>bold</strong>
        text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
        # *italic* → <em>italic</em>
        text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
        return text