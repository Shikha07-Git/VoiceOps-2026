# """Step 2: Knowledge Grounding & RAG Pipeline for ZentroMart.

# This module indexes the 21 knowledge base Markdown documents, the product catalog,
# and holiday calendar. It performs precedence-aware hybrid retrieval and grounded generation.
# """
# import csv
# import json
# import math
# import os
# import re
# import sys
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple, Any

# # Ensure UTF-8 on Windows
# if hasattr(sys.stdout, "reconfigure"):
#     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# if hasattr(sys.stderr, "reconfigure"):
#     sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# from .config import KB_DIR, DATA_DIR, PROJECT_ROOT, REFERENCE_DATE
# from .llm import get_embedding, generate_text
# from .timelines import compute_refund_window

# # Document hierarchy weights (KB-00.1)
# DOC_TYPE_WEIGHTS = {
#     "policy": 1.0,
#     "agent_guide": 0.95,
#     "help": 0.90,
#     "faq": 0.85,
#     "marketing": 0.75,
#     "meta": 0.70,
# }

# SUPERSEDED_PENALTY = 0.40  # Superseded documents must never override current policy


# def cosine_similarity(v1: List[float], v2: List[float]) -> float:
#     """Calculate cosine similarity between two float vectors."""
#     dot = sum(a * b for a, b in zip(v1, v2))
#     norm1 = math.sqrt(sum(a * a for a in v1))
#     norm2 = math.sqrt(sum(b * b for b in v2))
#     if norm1 == 0.0 or norm2 == 0.0:
#         return 0.0
#     return dot / (norm1 * norm2)


# class KnowledgeRetriever:
#     """Indexes and retrieves grounded knowledge from Markdown docs and product catalog."""

#     def __init__(self, cache_file: Optional[Path] = None):
#         self.chunks: List[Dict[str, Any]] = []
#         self.cache_file = cache_file or (PROJECT_ROOT / "sample_outputs" / "kb_embeddings_cache.json")
#         self.load_all_knowledge()

#     def parse_markdown_docs(self):
#         """Parse all 21 Markdown files in kb/ into sections with metadata."""
#         if not KB_DIR.exists():
#             return

#         for file_path in sorted(KB_DIR.glob("*.md")):
#             content = file_path.read_text(encoding="utf-8")
            
#             # Parse YAML frontmatter
#             frontmatter = {}
#             body = content
#             if content.startswith("---"):
#                 parts = content.split("---", 2)
#                 if len(parts) >= 3:
#                     yaml_text = parts[1]
#                     body = parts[2]
#                     for line in yaml_text.strip().split("\n"):
#                         if ":" in line:
#                             k, v = line.split(":", 1)
#                             frontmatter[k.strip()] = v.strip()

#             doc_id = frontmatter.get("doc_id", file_path.stem)
#             doc_title = frontmatter.get("title", file_path.stem)
#             doc_type = frontmatter.get("doc_type", "policy")
#             status = frontmatter.get("status", "current")
#             effective_from = frontmatter.get("effective_from", "")

#             # Split by section headers: ## [SECTION_ID] Section Title
#             section_pattern = r"(##\s*\[([^\]]+)\]\s*([^\n]+))"
#             matches = list(re.finditer(section_pattern, body))

#             if not matches:
#                 # Document without specific section tags
#                 self.chunks.append({
#                     "section_id": doc_id,
#                     "title": doc_title,
#                     "heading": doc_title,
#                     "doc_type": doc_type,
#                     "status": status,
#                     "effective_from": effective_from,
#                     "text": f"{doc_title}\n{body.strip()}",
#                     "source": file_path.name
#                 })
#             else:
#                 for i, match in enumerate(matches):
#                     sec_id = match.group(2).strip()
#                     sec_heading = match.group(3).strip()
#                     start_pos = match.start()
#                     end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(body)
#                     sec_body = body[start_pos:end_pos].strip()

#                     self.chunks.append({
#                         "section_id": sec_id,
#                         "title": doc_title,
#                         "heading": sec_heading,
#                         "doc_type": doc_type,
#                         "status": status,
#                         "effective_from": effective_from,
#                         "text": f"Document: {doc_title} ({doc_type}, {status})\nSection [{sec_id}] {sec_heading}\n{sec_body}",
#                         "source": file_path.name
#                     })

#     def parse_products_catalog(self):
#         """Index product catalog rows from data/products.csv."""
#         products_file = DATA_DIR / "products.csv"
#         if not products_file.exists():
#             return

#         with open(products_file, "r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 sku = row["sku"]
#                 title = row["title"]
#                 brand = row.get("brand", "")
#                 ret_cat = row.get("return_category", "")
#                 price = row.get("price_inr", "")
#                 fulfilled = row.get("fulfilled_by", "")
#                 assured_val = str(row.get("assured", "")).lower() == "true"
#                 warranty = row.get("warranty_months", "")
#                 desc = row.get("description", "")

#                 assured_text = "12-month ZentroMart Assured warranty in addition to brand warranty" if assured_val else "Not Assured"

#                 chunk_text = (
#                     f"Product: {title} | SKU: {sku} | Brand: {brand} | "
#                     f"Return Category: {ret_cat} | Price: ₹{price} | "
#                     f"Fulfilled by: {fulfilled} | ZentroMart Assured: {assured_val} ({assured_text}) | "
#                     f"Brand Warranty: {warranty} months. {desc}"
#                 )

#                 self.chunks.append({
#                     "section_id": f"products.csv:{sku}",
#                     "title": title,
#                     "heading": f"Product {sku}",
#                     "doc_type": "product",
#                     "status": "current",
#                     "effective_from": "2026-01-01",
#                     "text": chunk_text,
#                     "source": "products.csv",
#                     "sku": sku
#                 })

#     def load_all_knowledge(self):
#         """Load and index all Markdown and CSV knowledge sources."""
#         self.parse_markdown_docs()
#         self.parse_products_catalog()

#     def build_embeddings(self, force_refresh: bool = False):
#         """Generate or load embeddings for all chunks."""
#         self.cache_file.parent.mkdir(parents=True, exist_ok=True)
#         if not force_refresh and self.cache_file.exists():
#             print(f"[RAG] Loading embeddings from cache: {self.cache_file}...", flush=True)
#             with open(self.cache_file, "r", encoding="utf-8") as f:
#                 cache = json.load(f)
#             cached_vectors = cache.get("embeddings", {})
#             for chunk in self.chunks:
#                 cid = chunk["section_id"]
#                 if cid in cached_vectors:
#                     chunk["embedding"] = cached_vectors[cid]
            
#             # Check if all chunks have embeddings
#             missing = [c for c in self.chunks if "embedding" not in c]
#             if not missing:
#                 print(f"[RAG] Successfully loaded {len(self.chunks)} cached embeddings.", flush=True)
#                 return

#         print(f"[RAG] Generating batch embeddings for {len(self.chunks)} chunks via Gemini...", flush=True)
#         from .llm import get_embeddings_batch
        
#         texts_to_embed = [c["text"] for c in self.chunks]
#         vectors = get_embeddings_batch(texts_to_embed)
        
#         cached_vectors = {}
#         for chunk, vec in zip(self.chunks, vectors):
#             chunk["embedding"] = vec
#             cached_vectors[chunk["section_id"]] = vec

#         with open(self.cache_file, "w", encoding="utf-8") as f:
#             json.dump({"embeddings": cached_vectors}, f)
#         print(f"[RAG] Finished embedding all {len(self.chunks)} chunks and cached to {self.cache_file}.", flush=True)

#     def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
#         """Retrieve the most relevant knowledge chunks using hybrid semantic and precedence scoring."""
#         query_emb = get_embedding(query)
#         q_lower = query.lower()

#         # Check for explicit SKU mentions in query
#         sku_match = re.search(r"\b([A-Z]{3}-\d{4})\b", query, re.I)
#         target_sku = sku_match.group(1).upper() if sku_match else None

#         scored = []
#         for chunk in self.chunks:
#             if "embedding" not in chunk:
#                 continue

#             sim = cosine_similarity(query_emb, chunk["embedding"])

#             # Priority weight based on document type & status
#             weight = DOC_TYPE_WEIGHTS.get(chunk["doc_type"], 0.85)
#             if chunk["status"] == "superseded":
#                 weight *= SUPERSEDED_PENALTY

#             score = sim * weight

#             # Entity boost: direct SKU match
#             if target_sku and chunk.get("sku") == target_sku:
#                 score += 0.50

#             # Boost non-returnable categories policy (RET-5) for innerwear/briefs/perishables
#             if any(w in q_lower for w in ["briefs", "innerwear", "underwear", "panties", "boxers"]) and chunk.get("section_id") in ("RET-5", "RET-2"):
#                 score += 0.60

#             # Title or keyword match boost
#             if chunk.get("title", "").lower() in q_lower:
#                 score += 0.10

#             scored.append((score, chunk))

#         scored.sort(key=lambda x: x[0], reverse=True)
#         return [item[1] for item in scored[:top_k]]


# # Singleton instance
# _retriever: Optional[KnowledgeRetriever] = None


# def get_retriever() -> KnowledgeRetriever:
#     global _retriever
#     if _retriever is None:
#         _retriever = KnowledgeRetriever()
#         _retriever.build_embeddings()
#     return _retriever


# RAG_SYSTEM_PROMPT = (
#     "You are the customer support AI assistant for ZentroMart, an Indian online store "
#     "selling groceries and electronics. Always introduce yourself as an AI assistant in your reply.\n\n"
#     "CRITICAL GROUNDING RULES:\n"
#     "1. Base your answer STRICTLY and ONLY on the provided context sections.\n"
#     "2. If the context does NOT contain the necessary information to answer the question, "
#     "explicitly state that you do not have information about that in store policies, and offer to "
#     "connect the customer to a human colleague. NEVER invent or assume policies, amounts, or timelines.\n"
#     "3. Reference date: Today is 20 October 2026. Business days run Monday to Saturday (Sundays and "
#     "listed warehouse holidays are skipped: 15 Aug, 2 Oct, 19 Oct, 9 Nov). Return windows use calendar days.\n"
#     "4. Precedence: Policy > Agent Guide > Help > FAQ > Marketing. Superseded documents must not override current policy.\n"
#     "5. When reporting refund arrival dates, explicitly cite the exact arrival date or date range.\n"
#     "6. If the customer reports damaged high-value electronics (such as laptops or TVs worth >= ₹10,000), "
#     "or unauthorized order activity, per policy ESC-1 state that you are creating a ticket and connecting "
#     "them to our Priority Resolution team / human colleague.\n"
#     "7. Format your response politely and concisely. At the very end of your response, output on a new line: "
#     "Sources: [SECTION-ID-1, SECTION-ID-2, ...]"
# )


# def answer_with_rag(query: str, top_k: int = 4) -> Dict[str, Any]:
#     """Answer a customer query using RAG grounded in ZentroMart documents."""
#     retriever = get_retriever()
#     chunks = retriever.retrieve(query, top_k=top_k)

#     context_blocks = []
#     used_section_ids = []
#     for c in chunks:
#         context_blocks.append(f"--- Section [{c['section_id']}] ({c['source']}) ---\n{c['text']}")
#         used_section_ids.append(c["section_id"])

#     # Check for timeline question in query (e.g. 17 October 2026, 12 October 2026, 14 October 2026)
#     extra_calc = ""
#     date_match = re.search(r"(\d{1,2}\s+(?:october|oct)\s+2026)", query, re.I)
#     if date_match:
#         # Standardize date to YYYY-MM-DD
#         day = re.search(r"\d{1,2}", date_match.group(1)).group(0).zfill(2)
#         iso_date = f"2026-10-{day}"
#         method = "card" if any(w in query.lower() for w in ["card", "credit"]) else ("upi" if "upi" in query.lower() else "net")
#         min_d, max_d, phrase = compute_refund_window(iso_date, method)
#         if max_d:
#             extra_calc = (
#                 f"\n\n[OFFICIAL BUSINESS-DAY TIMELINE CALCULATION]\n"
#                 f"Refund initiated on {date_match.group(1)} via {method}. "
#                 f"Counting business days (Monday-Saturday, skipping Sundays and 19 October warehouse holiday): "
#                 f"{phrase}."
#             )

#     context_str = "\n\n".join(context_blocks) + extra_calc
#     prompt = (
#         f"CONTEXT INFORMATION:\n{context_str}\n\n"
#         f"CUSTOMER QUESTION:\n{query}\n\n"
#         "Provide a grounded, polite answer based strictly on the context above."
#     )

#     response = generate_text(prompt, system_instruction=RAG_SYSTEM_PROMPT, temperature=0.0)
    
#     # Extract declared sources if present
#     sources_match = re.search(r"Sources:\s*\[?([^\]\n]+)\]?", response, re.I)
#     reported_sources = [s.strip() for s in sources_match.group(1).split(",")] if sources_match else used_section_ids

#     return {
#         "query": query,
#         "response": response,
#         "used_section_ids": reported_sources,
#         "retrieved_chunks": used_section_ids
#     }

#######################################################################################################################################3333
# """Step 2: Knowledge Grounding & RAG Pipeline for ZentroMart.

# This module indexes the 21 knowledge base Markdown documents, the product catalog,
# and holiday calendar. It performs precedence-aware hybrid retrieval and grounded generation.
# """
# import csv
# import json
# import math
# import os
# import re
# import sys
# from pathlib import Path
# from typing import Dict, List, Optional, Tuple, Any

# # Ensure UTF-8 on Windows
# if hasattr(sys.stdout, "reconfigure"):
#     sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# if hasattr(sys.stderr, "reconfigure"):
#     sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# from .config import KB_DIR, DATA_DIR, PROJECT_ROOT, REFERENCE_DATE
# from .llm import get_embedding, generate_text
# from .timelines import compute_refund_window

# # Document hierarchy weights (KB-00.1)
# DOC_TYPE_WEIGHTS = {
#     "policy": 1.0,
#     "agent_guide": 0.95,
#     "help": 0.90,
#     "faq": 0.85,
#     "marketing": 0.75,
#     "meta": 0.70,
# }

# SUPERSEDED_PENALTY = 0.40  # Superseded documents must never override current policy

# # (query keywords, section ids to boost, bonus)
# SECTION_BOOSTS = [
#     (["briefs", "innerwear", "underwear", "panties", "boxers"], ["RET-5", "RET-2"], 0.60),
#     (["never placed", "didn't order", "did not order", "unauthori", "fraud", "hacked", "nahi kiya"], ["ESC-1", "IDV-4", "ESC-4"], 0.50),
#     (["phone number of", "address of", "who ordered", "someone else", "neighbour", "neighbor", "another person"], ["IDV-4", "ESC-4", "IDV-2"], 0.50),
#     (["warranty", "guarantee"], ["WAR-1", "WAR-2"], 0.40),
#     (["crack", "broken", "damaged", "damage", "defective", "dead on arrival", "kharab"], ["DWM-3", "ESC-1", "DWM-1"], 0.40),
#     (["refund"], ["REF-2", "KB-00.3"], 0.20),
# ]

# DAMAGE_WORDS = ["crack", "broken", "damaged", "damage", "defective", "dead on arrival", "kharab", "shattered"]
# FRAUD_WORDS = ["never placed", "didn't order", "did not order", "unauthorized", "unauthorised", "fraud", "hacked"]


# def cosine_similarity(v1: List[float], v2: List[float]) -> float:
#     """Calculate cosine similarity between two float vectors."""
#     dot = sum(a * b for a, b in zip(v1, v2))
#     norm1 = math.sqrt(sum(a * a for a in v1))
#     norm2 = math.sqrt(sum(b * b for b in v2))
#     if norm1 == 0.0 or norm2 == 0.0:
#         return 0.0
#     return dot / (norm1 * norm2)


# class KnowledgeRetriever:
#     """Indexes and retrieves grounded knowledge from Markdown docs and product catalog."""

#     def __init__(self, cache_file: Optional[Path] = None):
#         self.chunks: List[Dict[str, Any]] = []
#         self.cache_file = cache_file or (PROJECT_ROOT / "sample_outputs" / "kb_embeddings_cache.json")
#         self.load_all_knowledge()

#     def parse_markdown_docs(self):
#         """Parse all 21 Markdown files in kb/ into sections with metadata."""
#         if not KB_DIR.exists():
#             return

#         for file_path in sorted(KB_DIR.glob("*.md")):
#             content = file_path.read_text(encoding="utf-8")
            
#             # Parse YAML frontmatter
#             frontmatter = {}
#             body = content
#             if content.startswith("---"):
#                 parts = content.split("---", 2)
#                 if len(parts) >= 3:
#                     yaml_text = parts[1]
#                     body = parts[2]
#                     for line in yaml_text.strip().split("\n"):
#                         if ":" in line:
#                             k, v = line.split(":", 1)
#                             frontmatter[k.strip()] = v.strip()

#             doc_id = frontmatter.get("doc_id", file_path.stem)
#             doc_title = frontmatter.get("title", file_path.stem)
#             doc_type = frontmatter.get("doc_type", "policy")
#             status = frontmatter.get("status", "current")
#             effective_from = frontmatter.get("effective_from", "")

#             # Split by section headers: ## [SECTION_ID] Section Title
#             section_pattern = r"(##\s*\[([^\]]+)\]\s*([^\n]+))"
#             matches = list(re.finditer(section_pattern, body))

#             if not matches:
#                 # Document without specific section tags
#                 self.chunks.append({
#                     "section_id": doc_id,
#                     "title": doc_title,
#                     "heading": doc_title,
#                     "doc_type": doc_type,
#                     "status": status,
#                     "effective_from": effective_from,
#                     "text": f"{doc_title}\n{body.strip()}",
#                     "source": file_path.name
#                 })
#             else:
#                 for i, match in enumerate(matches):
#                     sec_id = match.group(2).strip()
#                     sec_heading = match.group(3).strip()
#                     start_pos = match.start()
#                     end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(body)
#                     sec_body = body[start_pos:end_pos].strip()

#                     self.chunks.append({
#                         "section_id": sec_id,
#                         "title": doc_title,
#                         "heading": sec_heading,
#                         "doc_type": doc_type,
#                         "status": status,
#                         "effective_from": effective_from,
#                         "text": f"Document: {doc_title} ({doc_type}, {status})\nSection [{sec_id}] {sec_heading}\n{sec_body}",
#                         "source": file_path.name
#                     })

#     def parse_products_catalog(self):
#         """Index product catalog rows from data/products.csv."""
#         products_file = DATA_DIR / "products.csv"
#         if not products_file.exists():
#             return

#         with open(products_file, "r", encoding="utf-8") as f:
#             reader = csv.DictReader(f)
#             for row in reader:
#                 sku = row["sku"]
#                 title = row["title"]
#                 brand = row.get("brand", "")
#                 ret_cat = row.get("return_category", "")
#                 price = row.get("price_inr", "")
#                 fulfilled = row.get("fulfilled_by", "")
#                 assured_val = str(row.get("assured", "")).lower() == "true"
#                 warranty = row.get("warranty_months", "")
#                 desc = row.get("description", "")

#                 assured_text = "12-month ZentroMart Assured warranty in addition to brand warranty" if assured_val else "Not Assured"

#                 chunk_text = (
#                     f"Product: {title} | SKU: {sku} | Brand: {brand} | "
#                     f"Return Category: {ret_cat} | Price: ₹{price} | "
#                     f"Fulfilled by: {fulfilled} | ZentroMart Assured: {assured_val} ({assured_text}) | "
#                     f"Brand Warranty: {warranty} months. {desc}"
#                 )

#                 self.chunks.append({
#                     "section_id": f"products.csv:{sku}",
#                     "title": title,
#                     "heading": f"Product {sku}",
#                     "doc_type": "product",
#                     "status": "current",
#                     "effective_from": "2026-01-01",
#                     "text": chunk_text,
#                     "source": "products.csv",
#                     "sku": sku
#                 })

#     def load_all_knowledge(self):
#         """Load and index all Markdown and CSV knowledge sources."""
#         self.parse_markdown_docs()
#         self.parse_products_catalog()

#     def build_embeddings(self, force_refresh: bool = False):
#         """Generate or load embeddings for all chunks."""
#         self.cache_file.parent.mkdir(parents=True, exist_ok=True)
#         if not force_refresh and self.cache_file.exists():
#             print(f"[RAG] Loading embeddings from cache: {self.cache_file}...", flush=True)
#             with open(self.cache_file, "r", encoding="utf-8") as f:
#                 cache = json.load(f)
#             cached_vectors = cache.get("embeddings", {})
#             for chunk in self.chunks:
#                 cid = chunk["section_id"]
#                 if cid in cached_vectors:
#                     chunk["embedding"] = cached_vectors[cid]
            
#             # Check if all chunks have embeddings
#             missing = [c for c in self.chunks if "embedding" not in c]
#             if not missing:
#                 print(f"[RAG] Successfully loaded {len(self.chunks)} cached embeddings.", flush=True)
#                 return

#         print(f"[RAG] Generating batch embeddings for {len(self.chunks)} chunks via Gemini...", flush=True)
#         from .llm import get_embeddings_batch
        
#         texts_to_embed = [c["text"] for c in self.chunks]
#         vectors = get_embeddings_batch(texts_to_embed)
        
#         cached_vectors = {}
#         for chunk, vec in zip(self.chunks, vectors):
#             chunk["embedding"] = vec
#             cached_vectors[chunk["section_id"]] = vec

#         with open(self.cache_file, "w", encoding="utf-8") as f:
#             json.dump({"embeddings": cached_vectors}, f)
#         print(f"[RAG] Finished embedding all {len(self.chunks)} chunks and cached to {self.cache_file}.", flush=True)

#     def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
#         """Retrieve the most relevant knowledge chunks using hybrid semantic and precedence scoring."""
#         query_emb = get_embedding(query)
#         q_lower = query.lower()

#         # Check for explicit SKU mentions in query
#         sku_match = re.search(r"\b([A-Z]{3}-\d{4})\b", query, re.I)
#         target_sku = sku_match.group(1).upper() if sku_match else None

#         scored = []
#         for chunk in self.chunks:
#             if "embedding" not in chunk:
#                 continue

#             sim = cosine_similarity(query_emb, chunk["embedding"])

#             # Priority weight based on document type & status
#             weight = DOC_TYPE_WEIGHTS.get(chunk["doc_type"], 0.85)
#             if chunk["status"] == "superseded":
#                 weight *= SUPERSEDED_PENALTY

#             score = sim * weight

#             # Entity boost: direct SKU match
#             if target_sku and chunk.get("sku") == target_sku:
#                 score += 0.50

#             # Keyword -> section boosts (entity routing)
#             for words, sections, bonus in SECTION_BOOSTS:
#                 if chunk.get("section_id") in sections and any(w in q_lower for w in words):
#                     score += bonus

#             # Title or keyword match boost
#             if chunk.get("title", "").lower() in q_lower:
#                 score += 0.10

#             scored.append((score, chunk))

#         scored.sort(key=lambda x: x[0], reverse=True)
#         rank = {id(c): i for i, (_, c) in enumerate(scored)}
#         top = [c for _, c in scored[:top_k]]

#         # Guarantee policy coverage: product rows must not crowd out policy sections
#         policy = [c for c in top if c["doc_type"] != "product"]
#         if len(policy) < 2:
#             in_top = {id(c) for c in top}
#             extras = [c for _, c in scored if c["doc_type"] != "product" and id(c) not in in_top][: 2 - len(policy)]
#             products = [c for c in top if c["doc_type"] == "product"]
#             products = products[: max(0, top_k - len(policy) - len(extras))]
#             top = sorted(policy + extras + products, key=lambda c: rank[id(c)])
#         return top


# # Singleton instance
# _retriever: Optional[KnowledgeRetriever] = None


# def get_retriever() -> KnowledgeRetriever:
#     global _retriever
#     if _retriever is None:
#         _retriever = KnowledgeRetriever()
#         _retriever.build_embeddings()
#     return _retriever


# RAG_SYSTEM_PROMPT = (
#     "You are the customer support AI assistant for ZentroMart, an Indian online store "
#     "selling groceries and electronics. Always introduce yourself as an AI assistant in your reply.\n\n"
#     "CRITICAL GROUNDING RULES:\n"
#     "1. Base your answer STRICTLY and ONLY on the provided context sections.\n"
#     "2. If the context does NOT contain the necessary information to answer the question, "
#     "explicitly state that you do not have information about that in store policies, and offer to "
#     "connect the customer to a human colleague. NEVER invent or assume policies, amounts, or timelines.\n"
#     "3. Reference date: Today is 20 October 2026. Business days run Monday to Saturday (Sundays and "
#     "listed warehouse holidays are skipped: 15 Aug, 2 Oct, 19 Oct, 9 Nov). Return windows use calendar days.\n"
#     "4. Precedence: Policy > Agent Guide > Help > FAQ > Marketing. Superseded documents must not override current policy.\n"
#     "5. When reporting refund arrival dates, explicitly cite the exact arrival date or date range.\n"
#     "6. If the customer reports damaged high-value electronics (such as laptops or TVs worth >= ₹10,000), "
#     "or unauthorized order activity, per policy ESC-1 state that you are creating a ticket and connecting "
#     "them to our Priority Resolution team / human colleague.\n"
#     "7. Format your response politely and concisely. At the very end of your response, output on a new line: "
#     "Sources: [SECTION-ID-1, SECTION-ID-2, ...]"
# )


# def answer_with_rag(query: str, top_k: int = 4) -> Dict[str, Any]:
#     """Answer a customer query using RAG grounded in ZentroMart documents."""
#     retriever = get_retriever()
#     chunks = retriever.retrieve(query, top_k=top_k)

#     context_blocks = []
#     used_section_ids = []
#     for c in chunks:
#         context_blocks.append(f"--- Section [{c['section_id']}] ({c['source']}) ---\n{c['text']}")
#         used_section_ids.append(c["section_id"])

#     # Check for timeline question in query (e.g. 17 October 2026, 12 October 2026, 14 October 2026)
#     extra_calc = ""
#     date_match = re.search(r"(\d{1,2}\s+(?:october|oct)\s+2026)", query, re.I)
#     if date_match and "refund" in query.lower():
#         # Standardize date to YYYY-MM-DD
#         day = re.search(r"\d{1,2}", date_match.group(1)).group(0).zfill(2)
#         iso_date = f"2026-10-{day}"
#         method = "card" if any(w in query.lower() for w in ["card", "credit"]) else ("upi" if "upi" in query.lower() else "net")
#         min_d, max_d, phrase = compute_refund_window(iso_date, method)
#         if max_d:
#             extra_calc = (
#                 f"\n\n[OFFICIAL BUSINESS-DAY TIMELINE CALCULATION]\n"
#                 f"Refund initiated on {date_match.group(1)} via {method}. "
#                 f"Counting business days (Monday-Saturday, skipping Sundays and 19 October warehouse holiday): "
#                 f"{phrase}."
#             )

#     # Deterministic ESC-1 detection: damaged product priced >= Rs 10,000, or unauthorized activity
#     q_lower = query.lower()
#     escalate = any(w in q_lower for w in FRAUD_WORDS)
#     if not escalate and any(w in q_lower for w in DAMAGE_WORDS):
#         sku_m = re.search(r"\b([A-Z]{3}-\d{4})\b", query, re.I)
#         sku = sku_m.group(1).upper() if sku_m else None
#         for c in chunks:
#             if c["doc_type"] != "product":
#                 continue
#             if (sku and c.get("sku") == sku) or (not sku and c.get("title", "").lower() in q_lower):
#                 pm = re.search(r"Price:\s*₹\s*([\d,]+(?:\.\d+)?)", c["text"])
#                 if pm and float(pm.group(1).replace(",", "")) >= 10000:
#                     escalate = True
#     esc_note = ""
#     if escalate:
#         esc_note = (
#             "\n\n[ESCALATION REQUIRED - ESC-1]\n"
#             "This case must be escalated. Tell the customer you are creating a support ticket and connecting them to the "
#             "Priority Resolution team / a human colleague. Do not approve any refund or replacement yourself."
#         )

#     context_str = "\n\n".join(context_blocks) + extra_calc + esc_note
#     prompt = (
#         f"CONTEXT INFORMATION:\n{context_str}\n\n"
#         f"CUSTOMER QUESTION:\n{query}\n\n"
#         "Provide a grounded, polite answer based strictly on the context above."
#     )

#     response = generate_text(prompt, system_instruction=RAG_SYSTEM_PROMPT, temperature=0.0)
    
#     # Extract declared sources if present
#     sources_match = re.search(r"Sources:\s*\[?([^\]\n]+)\]?", response, re.I)
#     reported_sources = [s.strip() for s in sources_match.group(1).split(",")] if sources_match else used_section_ids

#     return {
#         "query": query,
#         "response": response,
#         "used_section_ids": reported_sources,
#         "retrieved_chunks": used_section_ids,
#         "escalate": escalate
#     }


"""Step 2: Knowledge Grounding & RAG Pipeline for ZentroMart.

This module indexes the 21 knowledge base Markdown documents, the product catalog,
and holiday calendar. It performs precedence-aware hybrid retrieval and grounded generation.
"""
import csv
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure UTF-8 on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from .config import KB_DIR, DATA_DIR, PROJECT_ROOT, REFERENCE_DATE
from .llm import get_embedding, generate_text
from .timelines import compute_refund_window

# Document hierarchy weights (KB-00.1)
DOC_TYPE_WEIGHTS = {
    "policy": 1.0,
    "agent_guide": 0.95,
    "help": 0.90,
    "faq": 0.85,
    "marketing": 0.75,
    "meta": 0.70,
}

SUPERSEDED_PENALTY = 0.40  # Superseded documents must never override current policy

# (query keywords, section ids to boost, bonus)
SECTION_BOOSTS = [
    (["briefs", "innerwear", "underwear", "panties", "boxers"], ["RET-5", "RET-2"], 0.60),
    (["never placed", "didn't order", "did not order", "unauthori", "fraud", "hacked", "nahi kiya"], ["ESC-1", "IDV-4", "ESC-4"], 0.50),
    (["phone number of", "address of", "who ordered", "someone else", "neighbour", "neighbor", "another person"], ["IDV-4", "ESC-4", "IDV-2"], 0.50),
    (["warranty", "guarantee"], ["WAR-1", "WAR-2"], 0.40),
    (["crack", "broken", "damaged", "damage", "defective", "dead on arrival", "kharab"], ["DWM-3", "ESC-1", "DWM-1"], 0.40),
    (["refund"], ["REF-2", "KB-00.3"], 0.20),
]

DAMAGE_WORDS = ["crack", "broken", "damaged", "damage", "defective", "dead on arrival", "kharab", "shattered"]
FRAUD_WORDS = ["never placed", "didn't order", "did not order", "unauthorized", "unauthorised", "fraud", "hacked"]


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two float vectors."""
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return dot / (norm1 * norm2)


class KnowledgeRetriever:
    """Indexes and retrieves grounded knowledge from Markdown docs and product catalog."""

    def __init__(self, cache_file: Optional[Path] = None):
        self.chunks: List[Dict[str, Any]] = []
        self.cache_file = cache_file or (PROJECT_ROOT / "sample_outputs" / "kb_embeddings_cache.json")
        self.load_all_knowledge()

    def parse_markdown_docs(self):
        """Parse all 21 Markdown files in kb/ into sections with metadata."""
        if not KB_DIR.exists():
            return

        for file_path in sorted(KB_DIR.glob("*.md")):
            content = file_path.read_text(encoding="utf-8")
            
            # Parse YAML frontmatter
            frontmatter = {}
            body = content
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    yaml_text = parts[1]
                    body = parts[2]
                    for line in yaml_text.strip().split("\n"):
                        if ":" in line:
                            k, v = line.split(":", 1)
                            frontmatter[k.strip()] = v.strip()

            doc_id = frontmatter.get("doc_id", file_path.stem)
            doc_title = frontmatter.get("title", file_path.stem)
            doc_type = frontmatter.get("doc_type", "policy")
            status = frontmatter.get("status", "current")
            effective_from = frontmatter.get("effective_from", "")

            # Split by section headers: ## [SECTION_ID] Section Title
            section_pattern = r"(##\s*\[([^\]]+)\]\s*([^\n]+))"
            matches = list(re.finditer(section_pattern, body))

            if not matches:
                # Document without specific section tags
                self.chunks.append({
                    "section_id": doc_id,
                    "title": doc_title,
                    "heading": doc_title,
                    "doc_type": doc_type,
                    "status": status,
                    "effective_from": effective_from,
                    "text": f"{doc_title}\n{body.strip()}",
                    "source": file_path.name
                })
            else:
                for i, match in enumerate(matches):
                    sec_id = match.group(2).strip()
                    sec_heading = match.group(3).strip()
                    start_pos = match.start()
                    end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(body)
                    sec_body = body[start_pos:end_pos].strip()

                    self.chunks.append({
                        "section_id": sec_id,
                        "title": doc_title,
                        "heading": sec_heading,
                        "doc_type": doc_type,
                        "status": status,
                        "effective_from": effective_from,
                        "text": f"Document: {doc_title} ({doc_type}, {status})\nSection [{sec_id}] {sec_heading}\n{sec_body}",
                        "source": file_path.name
                    })

    def parse_products_catalog(self):
        """Index product catalog rows from data/products.csv."""
        products_file = DATA_DIR / "products.csv"
        if not products_file.exists():
            return

        with open(products_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                sku = row["sku"]
                title = row["title"]
                brand = row.get("brand", "")
                ret_cat = row.get("return_category", "")
                price = row.get("price_inr", "")
                fulfilled = row.get("fulfilled_by", "")
                assured_val = str(row.get("assured", "")).lower() == "true"
                warranty = row.get("warranty_months", "")
                desc = row.get("description", "")

                assured_text = "12-month ZentroMart Assured warranty in addition to brand warranty" if assured_val else "Not Assured"

                chunk_text = (
                    f"Product: {title} | SKU: {sku} | Brand: {brand} | "
                    f"Return Category: {ret_cat} | Price: ₹{price} | "
                    f"Fulfilled by: {fulfilled} | ZentroMart Assured: {assured_val} ({assured_text}) | "
                    f"Brand Warranty: {warranty} months. {desc}"
                )

                self.chunks.append({
                    "section_id": f"products.csv:{sku}",
                    "title": title,
                    "heading": f"Product {sku}",
                    "doc_type": "product",
                    "status": "current",
                    "effective_from": "2026-01-01",
                    "text": chunk_text,
                    "source": "products.csv",
                    "sku": sku
                })

    def load_all_knowledge(self):
        """Load and index all Markdown and CSV knowledge sources."""
        self.parse_markdown_docs()
        self.parse_products_catalog()

    def build_embeddings(self, force_refresh: bool = False):
        """Generate or load embeddings for all chunks."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        if not force_refresh and self.cache_file.exists():
            print(f"[RAG] Loading embeddings from cache: {self.cache_file}...", flush=True)
            with open(self.cache_file, "r", encoding="utf-8") as f:
                cache = json.load(f)
            cached_vectors = cache.get("embeddings", {})
            for chunk in self.chunks:
                cid = chunk["section_id"]
                if cid in cached_vectors:
                    chunk["embedding"] = cached_vectors[cid]
            
            # Check if all chunks have embeddings
            missing = [c for c in self.chunks if "embedding" not in c]
            if not missing:
                print(f"[RAG] Successfully loaded {len(self.chunks)} cached embeddings.", flush=True)
                return

        print(f"[RAG] Generating batch embeddings for {len(self.chunks)} chunks via Gemini...", flush=True)
        from .llm import get_embeddings_batch
        
        texts_to_embed = [c["text"] for c in self.chunks]
        vectors = get_embeddings_batch(texts_to_embed)
        
        cached_vectors = {}
        for chunk, vec in zip(self.chunks, vectors):
            chunk["embedding"] = vec
            cached_vectors[chunk["section_id"]] = vec

        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump({"embeddings": cached_vectors}, f)
        print(f"[RAG] Finished embedding all {len(self.chunks)} chunks and cached to {self.cache_file}.", flush=True)

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Retrieve the most relevant knowledge chunks using hybrid semantic and precedence scoring."""
        query_emb = get_embedding(query)
        q_lower = query.lower()

        # Check for explicit SKU mentions in query
        sku_match = re.search(r"\b([A-Z]{3}-\d{4})\b", query, re.I)
        target_sku = sku_match.group(1).upper() if sku_match else None

        scored = []
        for chunk in self.chunks:
            if "embedding" not in chunk:
                continue

            sim = cosine_similarity(query_emb, chunk["embedding"])

            # Priority weight based on document type & status
            weight = DOC_TYPE_WEIGHTS.get(chunk["doc_type"], 0.85)
            if chunk["status"] == "superseded":
                weight *= SUPERSEDED_PENALTY

            score = sim * weight

            # Entity boost: direct SKU match
            if target_sku and chunk.get("sku") == target_sku:
                score += 0.50

            # Keyword -> section boosts (entity routing)
            for words, sections, bonus in SECTION_BOOSTS:
                if chunk.get("section_id") in sections and any(w in q_lower for w in words):
                    score += bonus

            # Title or keyword match boost
            if chunk.get("title", "").lower() in q_lower:
                score += 0.10

            scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        rank = {id(c): i for i, (_, c) in enumerate(scored)}
        top = [c for _, c in scored[:top_k]]

        # Guarantee policy coverage: product rows must not crowd out policy sections
        policy = [c for c in top if c["doc_type"] != "product"]
        if len(policy) < 2:
            in_top = {id(c) for c in top}
            extras = [c for _, c in scored if c["doc_type"] != "product" and id(c) not in in_top][: 2 - len(policy)]
            products = [c for c in top if c["doc_type"] == "product"]
            products = products[: max(0, top_k - len(policy) - len(extras))]
            top = sorted(policy + extras + products, key=lambda c: rank[id(c)])
        return top


# Singleton instance
_retriever: Optional[KnowledgeRetriever] = None


def get_retriever() -> KnowledgeRetriever:
    global _retriever
    if _retriever is None:
        _retriever = KnowledgeRetriever()
        _retriever.build_embeddings()
    return _retriever


RAG_SYSTEM_PROMPT = (
    "You are the customer support AI assistant for ZentroMart, an Indian online store "
    "selling groceries and electronics. Always introduce yourself as an AI assistant in your reply.\n\n"
    "CRITICAL GROUNDING RULES:\n"
    "1. Base your answer STRICTLY and ONLY on the provided context sections.\n"
    "2. If the context does NOT contain the necessary information to answer the question, "
    "explicitly state that you do not have information about that in store policies, and offer to "
    "connect the customer to a human colleague. NEVER invent or assume policies, amounts, or timelines.\n"
    "3. Reference date: Today is 20 October 2026. Business days run Monday to Saturday (Sundays and "
    "listed warehouse holidays are skipped: 15 Aug, 2 Oct, 19 Oct, 9 Nov). Return windows use calendar days.\n"
    "4. Precedence: Policy > Agent Guide > Help > FAQ > Marketing. Superseded documents must not override current policy.\n"
    "5. When reporting refund arrival dates, explicitly cite the exact arrival date or date range.\n"
    "6. If the customer reports damaged high-value electronics (such as laptops or TVs worth >= ₹10,000), "
    "or unauthorized order activity, per policy ESC-1 state that you are creating a ticket and connecting "
    "them to our Priority Resolution team / human colleague.\n"
    "7. For compensation, voucher or goodwill requests: politely say policy does not allow it; the system handles the human handover.\n"
    "8. Format your response politely and concisely. At the very end of your response, output on a new line: "
    "Sources: [SECTION-ID-1, SECTION-ID-2, ...]"
)


def answer_with_rag(query: str, top_k: int = 4) -> Dict[str, Any]:
    """Answer a customer query using RAG grounded in ZentroMart documents."""
    retriever = get_retriever()
    chunks = retriever.retrieve(query, top_k=top_k)

    context_blocks = []
    used_section_ids = []
    for c in chunks:
        context_blocks.append(f"--- Section [{c['section_id']}] ({c['source']}) ---\n{c['text']}")
        used_section_ids.append(c["section_id"])

    # Check for timeline question in query (e.g. 17 October 2026, 12 October 2026, 14 October 2026)
    extra_calc = ""
    date_match = re.search(r"(\d{1,2}\s+(?:october|oct)\s+2026)", query, re.I)
    if date_match and "refund" in query.lower():
        # Standardize date to YYYY-MM-DD
        day = re.search(r"\d{1,2}", date_match.group(1)).group(0).zfill(2)
        iso_date = f"2026-10-{day}"
        method = "card" if any(w in query.lower() for w in ["card", "credit"]) else ("upi" if "upi" in query.lower() else "net")
        min_d, max_d, phrase = compute_refund_window(iso_date, method)
        if max_d:
            extra_calc = (
                f"\n\n[OFFICIAL BUSINESS-DAY TIMELINE CALCULATION]\n"
                f"Refund initiated on {date_match.group(1)} via {method}. "
                f"Counting business days (Monday-Saturday, skipping Sundays and 19 October warehouse holiday): "
                f"{phrase}."
            )

    # Deterministic ESC-1 detection: damaged product priced >= Rs 10,000, or unauthorized activity
    q_lower = query.lower()
    escalate = any(w in q_lower for w in FRAUD_WORDS)
    if not escalate and any(w in q_lower for w in DAMAGE_WORDS):
        sku_m = re.search(r"\b([A-Z]{3}-\d{4})\b", query, re.I)
        sku = sku_m.group(1).upper() if sku_m else None
        for c in chunks:
            if c["doc_type"] != "product":
                continue
            if (sku and c.get("sku") == sku) or (not sku and c.get("title", "").lower() in q_lower):
                pm = re.search(r"Price:\s*₹\s*([\d,]+(?:\.\d+)?)", c["text"])
                if pm and float(pm.group(1).replace(",", "")) >= 10000:
                    escalate = True
    esc_note = ""
    if escalate:
        esc_note = (
            "\n\n[ESCALATION REQUIRED - ESC-1]\n"
            "This case must be escalated. Tell the customer you are creating a support ticket and connecting them to the "
            "Priority Resolution team / a human colleague. Do not approve any refund or replacement yourself."
        )

    context_str = "\n\n".join(context_blocks) + extra_calc + esc_note
    prompt = (
        f"CONTEXT INFORMATION:\n{context_str}\n\n"
        f"CUSTOMER QUESTION:\n{query}\n\n"
        "Provide a grounded, polite answer based strictly on the context above."
    )

    response = generate_text(prompt, system_instruction=RAG_SYSTEM_PROMPT, temperature=0.0)
    
    # Extract declared sources if present
    sources_match = re.search(r"Sources:\s*\[?([^\]\n]+)\]?", response, re.I)
    reported_sources = [s.strip() for s in sources_match.group(1).split(",")] if sources_match else used_section_ids

    return {
        "query": query,
        "response": response,
        "used_section_ids": reported_sources,
        "retrieved_chunks": used_section_ids,
        "escalate": escalate
    }
