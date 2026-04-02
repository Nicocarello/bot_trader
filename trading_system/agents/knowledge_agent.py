import os
import logging
import glob
from google import genai
from typing import List, Optional
from datetime import datetime, timezone
from schemas.models import RAGContext, TradeProposal

logger = logging.getLogger(__name__)

class KnowledgeAgent:
    """
    RAG-Lite Agent: Consults a local 'knowledge/' directory of trading books/notes.
    Uses Gemini to verify if a trade setup aligns with 'The Masters' (Minervini, Weinstein, etc).
    """

    def __init__(self, knowledge_dir: str = "trading_system/knowledge"):
        self.knowledge_dir = knowledge_dir
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model_id = 'gemini-2.5-flash'
        else:
            self.client = None

    def _load_knowledge_text(self) -> str:
        """Reads all .md and .txt files from the knowledge directory."""
        content_found = []
        # Support both the specific folder and a relative path
        paths = [
            os.path.join(self.knowledge_dir, "*.md"),
            os.path.join(self.knowledge_dir, "*.txt")
        ]
        
        for path in paths:
            for filename in glob.glob(path):
                try:
                    with open(filename, 'r', encoding='utf-8') as f:
                        content_found.append(f"--- SOURCE: {os.path.basename(filename)} ---\n{f.read()}")
                except Exception as e:
                    logger.error(f"Error reading knowledge file {filename}: {e}")
        
        return "\n\n".join(content_found) if content_found else ""

    def consult_masters(self, asset: str, proposal: TradeProposal) -> RAGContext:
        """
        Consults the loaded knowledge library to validate the trade proposal.
        """
        knowledge_base = self._load_knowledge_text()
        
        if not self.client or not knowledge_base:
            reason = "No Gemini API key." if not self.client else "Knowledge folder is empty. (Add .md files!)"
            return RAGContext(
                query=f"Validate {asset} {proposal.decision} setup",
                top_k_chunks=[],
                source_documents=["N/A"],
                retrieval_confidence=0.0
            )

        try:
            prompt = f"""
            Identify if the following trade proposal aligns with the principles in your core knowledge library.
            
            KNOWLEDGE LIBRARY (The Masters):
            {knowledge_base[:30000]} # Limit to 30k chars for fast processing
            
            TRADE PROPOSAL:
            Asset: {asset}
            Decision: {proposal.decision}
            Reasoning: {proposal.reasoning}
            
            YOUR TASK:
            1. Search the library for rules regarding {proposal.decision} entries (e.g., Minervini's Volatility Contraction, Weinstein's Stage 2).
            2. Match the 'Reasoning' provided to these rules.
            3. Return a JSON object:
            {{
              "confidence": (float between 0.0 and 1.0, where 1.0 is perfect alignment),
              "snippets": ["Short 1-sentence quotes that support or reject this trade"],
              "summary": "1-sentence summary of alignment"
            }}
            """

            response = self.client.models.generate_content(
                model=self.model_id,
                contents=prompt
            )
            text = response.text.strip().replace("```json", "").replace("```", "")
            
            import json
            res = json.loads(text)
            
            logger.info(f"  [KNOWLEDGE] Alignment for {asset}: {res.get('confidence')} | {res.get('summary')}")
            
            return RAGContext(
                query=res.get("summary", "N/A"),
                top_k_chunks=res.get("snippets", []),
                source_documents=["local_knowledge_library"],
                retrieval_confidence=res.get("confidence", 0.5)
            )

        except Exception as e:
            logger.error(f"Error in KnowledgeAgent: {e}")
            return RAGContext(
                query=f"Consultation Failed: {e}",
                top_k_chunks=[],
                source_documents=[],
                retrieval_confidence=0.1
            )
