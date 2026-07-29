# Graph Report - .  (2026-07-24)

## Corpus Check
- 141 files · ~71,124 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 877 nodes · 1617 edges · 63 communities (45 shown, 18 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 57 edges (avg confidence: 0.76)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Project Overview & Architecture
- Hybrid PDF/DOCX Extraction
- RAGAS Evaluation Framework
- Document Extraction Pipeline
- UI Alert & Dropdown Components
- Frontend Dependencies
- Page Layouts
- TypeScript Configuration
- Chat UI Components
- LangGraph Agent Orchestration
- Frontend Build Tools
- Hybrid Retrieval Agent
- Temporal Workflow Activities
- UI Component System
- Documents API
- Document Chunking
- Metrics & Monitoring API
- Auth & Upload API
- User Interface Pages
- Summarizer Agent
- Vector Embedding & Storage
- Admin Dashboard
- Intent Classification
- Query Rewriting
- Message & Query DB
- API Routes
- MinIO Object Storage
- User & Auth UI
- Auth API
- Sessions API
- Users Admin API
- Load Testing
- Knowledge Vault UI
- Training Needs Analysis
- Verifier Agent
- Temporal Ingestion Workflow
- Offline Evaluation
- Conversation Memory
- Chat Page
- Executor Agent
- FastAPI Entry Point
- Temporal Package
- Web Search Tool
- Test Fixtures
- Calculator Tool
- Evaluation Package
- Backend Package
- Memory Package
- Tools Package
- Scripts Package
- Tests Package
- ESLint Config
- Next.js Config
- PostCSS Config
- File & Window Icons
- Next.js & Vercel Logos
- Backend README
- Backup Guide
- Globe Icon
- Frontend README
- Backend Module
- Pre-commit Config

## God Nodes (most connected - your core abstractions)
1. `cn()` - 65 edges
2. `fetch_one()` - 24 edges
3. `build_agent_graph()` - 21 edges
4. `GraphState` - 20 edges
5. `fetch_all()` - 18 edges
6. `Implementation Plan v3.1` - 18 edges
7. `get_llm()` - 17 edges
8. `compilerOptions` - 16 edges
9. `EnterpriseMind AI Architecture` - 16 edges
10. `EnterpriseMind AI SRS and PRD` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Milvus Vector Database` --semantically_similar_to--> `Chroma Vector Store`  [INFERRED] [semantically similar]
  backend/docker-compose.yml → ARCHITECTURE.md
- `Hybrid Page-Level Router Implementation` --semantically_similar_to--> `Implementation Plan: Hybrid Page-Level Router v2`  [INFERRED] [semantically similar]
  implementation_plan2.md → .opencode/plans/implementation-new-architecture.md
- `Implementation Plan v3.1` --semantically_similar_to--> `Hybrid Page-Level Router Implementation`  [INFERRED] [semantically similar]
  IMPLEMENTATION_PLAN.md → implementation_plan2.md
- `Hash-based Deduplication` --semantically_similar_to--> `Cross-Encoder Reranker`  [INFERRED] [semantically similar]
  DECISION_LOG.md → IMPLEMENTATION_PLAN.md
- `Supabase for Metadata Management` --semantically_similar_to--> `PostgreSQL with asyncpg`  [INFERRED] [semantically similar]
  DECISION_LOG.md → CHANGELOG.md

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Multi-Agent Query Pipeline** — concept_multi_agent_orchestration, concept_tiered_intent_classification, concept_hybrid_retrieval, concept_cross_encoder_reranker, concept_confidence_scoring, concept_reflection_loop, concept_citation_source_tracing [INFERRED 0.90]
- **Document Ingestion Pipeline** — concept_pymupdf4llm_extraction, concept_docling_vlm, concept_4_route_classification, concept_docling_sub_batching, concept_parent_child_chunking, concept_bge_m3_embedding, concept_hash_based_deduplication, concept_temporal_io [INFERRED 0.90]
- **Retrieval Quality Improvement Pipeline** — concept_hybrid_retrieval, concept_adaptive_top_k, concept_sastrawi_stemming, concept_query_expansion_decision_tree, concept_cross_encoder_reranker, concept_parent_child_chunking, concept_evaluation_driven_development [INFERRED 0.85]
- **CCA-DNA-TNA Organizational Learning Analysis Framework** — output1_image_cca, output1_image_dna, output1_image_tna [EXTRACTED 0.95]
- **TNA Derived Issues (Business, Performance, Competency)** — output1_image_tna, output1_image_business_issue, output1_image_performance_issue, output1_image_competency_issue [EXTRACTED 0.95]
- **Analysis Process to Stakeholder Mapping** — output1_image_cca, output1_image_top_management, output1_image_dna, output1_image_pemangku_jabatan, output1_image_tna, output1_image_unit_kerja [EXTRACTED 0.90]

## Communities (63 total, 18 thin omitted)

### Community 0 - "Project Overview & Architecture"
Cohesion: 0.08
Nodes (58): AI Coding Agent Rules, EnterpriseMind AI Architecture, Docker Compose Services, EnterpriseMind AI Changelog, Coding Standards, 4-Route Page Classification, Adaptive Top-K Retrieval, BAAI/bge-m3 Multilingual Embedding (+50 more)

### Community 1 - "Hybrid PDF/DOCX Extraction"
Cohesion: 0.08
Nodes (43): _build_mini_pdf(), _calculate_text_ratio(), classify_visual_page(), content_hash(), detect_file_type(), _extract_docx(), _extract_pdf(), _extract_pdf_with_pages() (+35 more)

### Community 2 - "RAGAS Evaluation Framework"
Cohesion: 0.07
Nodes (36): _get_metrics(), RAGAS Runner — EnterpriseMind AI.  Mengeksekusi evaluasi dan menghitung metrik R, Jalankan evaluasi perbandingan Naive RAG vs Agentic RAG.      Returns:         D, Jalankan evaluasi RAGAS pada test set.      Args:         graph_runner_func: Fun, run_comparison_evaluation(), run_evaluation(), Inisialisasi saat aplikasi dimulai. Pre-load models untuk eliminate cold start., startup_event() (+28 more)

### Community 3 - "Document Extraction Pipeline"
Cohesion: 0.10
Nodes (37): _build_mini_pdf(), clean_extraction_text(), content_hash(), _detect_table_pages(), _extract_docx(), _extract_pdf(), _extract_pdf_with_pages(), extract_text() (+29 more)

### Community 4 - "UI Alert & Dropdown Components"
Cohesion: 0.10
Nodes (23): Alert(), AlertAction(), AlertDescription(), AlertTitle(), alertVariants, CardAction(), DropdownMenuCheckboxItem(), DropdownMenuContent() (+15 more)

### Community 5 - "Frontend Dependencies"
Cohesion: 0.06
Nodes (33): @base-ui/react, class-variance-authority, clsx, framer-motion, dependencies, @base-ui/react, class-variance-authority, clsx (+25 more)

### Community 6 - "Page Layouts"
Cohesion: 0.09
Nodes (17): geist, metadata, RootLayout(), ErrorBoundary, Props, State, ProcessRail(), UserSideNavBar() (+9 more)

### Community 7 - "TypeScript Configuration"
Cohesion: 0.07
Nodes (28): compilerOptions, allowJs, esModuleInterop, incremental, isolatedModules, jsx, lib, module (+20 more)

### Community 8 - "Chat UI Components"
Cohesion: 0.15
Nodes (20): CitationCard(), CitationCardProps, MessageBubbleProps, Badge(), badgeVariants, Card(), CardContent(), CardFooter() (+12 more)

### Community 9 - "LangGraph Agent Orchestration"
Cohesion: 0.12
Nodes (23): _get_graph(), Lazy init — build once, reuse., build_agent_graph(), Graph Builder — EnterpriseMind AI.  Perakitan LangGraph multi-agent. SATU-SATUNY, Wrapper: catat elapsed time per node, enforce deadline via query_deadline., Routing setelah Orchestrator: ke Researcher atau langsung Summarizer.      Ref:, Routing setelah Verifier: ke Summarizer atau Reflection loop.      Ref: FR2.5 —, Routing setelah Summarizer: ke Executor atau END.      Ref: FR2.7 — Executor han (+15 more)

### Community 10 - "Frontend Build Tools"
Cohesion: 0.08
Nodes (25): eslint, eslint-config-next, devDependencies, eslint, eslint-config-next, tailwindcss, @tailwindcss/postcss, @types/node (+17 more)

### Community 11 - "Hybrid Retrieval Agent"
Cohesion: 0.12
Nodes (21): adaptive_top_k(), _build_parent_store(), Retriever Agent — EnterpriseMind AI.  Hybrid retrieval (vector + keyword) from k, Retrieve relevant documents with query expansion, adaptive top-k, reranking, and, Tentukan top-k berdasarkan multi-signal.     Ini adalah retrieval k (sebelum rer, Extract unique parent_ids from child chunks., Build parent store dari Milvus berdasarkan parent_ids., _resolve_parent_ids() (+13 more)

### Community 12 - "Temporal Workflow Activities"
Cohesion: 0.16
Nodes (20): chunk_document_activity(), cleanup_temp_file_activity(), create_document_record_activity(), detect_file_type_activity(), download_from_minio_activity(), embed_and_store_activity(), extract_text_activity(), Temporal Activities — EnterpriseMind AI.  Individual tasks that can be executed (+12 more)

### Community 13 - "UI Component System"
Cohesion: 0.09
Nodes (21): aliases, components, hooks, lib, ui, utils, iconLibrary, menuAccent (+13 more)

### Community 14 - "Documents API"
Cohesion: 0.15
Nodes (18): list_documents(), Documents API — EnterpriseMind AI.  Endpoint untuk mengelola dokumen (list, hapu, Ambil semua dokumen beserta metadata., Hapus dokumen dari Supabase dan Chroma.      Args:         document_id: UUID dar, remove_document(), create_document(), delete_document(), get_all_documents() (+10 more)

### Community 15 - "Document Chunking"
Cohesion: 0.18
Nodes (17): chunk_document(), chunk_document_parent_child(), chunk_pages(), content_hash(), DocumentChunk, normalize_for_hash(), Document Chunker — EnterpriseMind AI.  Parent-Child Chunking Strategy: - Parent, Split text into child chunks (untuk backward compatibility).     Gunakan chunk_d (+9 more)

### Community 16 - "Metrics & Monitoring API"
Cohesion: 0.15
Nodes (17): _empty_metrics(), get_dashboard_metrics(), Metrics API — EnterpriseMind AI.  Endpoint untuk dashboard admin (FR7.1). Mengam, Hitung dan kembalikan metrik dashboard utama., close_pool(), fetch_all(), fetch_val(), get_pool() (+9 more)

### Community 17 - "Auth & Upload API"
Cohesion: 0.16
Nodes (13): Upload API — EnterpriseMind AI.  POST /api/upload — Upload document and start as, create_access_token(), decode_access_token(), get_current_user(), Request, Auth Utilities — EnterpriseMind AI.  JWT generation/validation + bcrypt password, Create JWT access token.     Payload should include: sub, role, department, clea, Decode JWT. Raises HTTPException 401 if invalid. (+5 more)

### Community 18 - "User Interface Pages"
Cohesion: 0.22
Nodes (13): UserData, Session, UserSideNavBarProps, Button(), buttonVariants, Dialog(), DialogClose(), DialogContent() (+5 more)

### Community 19 - "Summarizer Agent"
Cohesion: 0.16
Nodes (16): _ensure_markdown_table(), _get_doc_field(), _parse_summarizer_response(), Summarizer Agent — EnterpriseMind AI.  Synthesize final answer from verified doc, Parse response into answer text and citations list. Only documents whose names a, Get field from doc dict, checking both top-level and nested metadata., Convert TAB-separated or multi-space tables to Markdown pipe format., Synthesize answer with citations from verified documents. (+8 more)

### Community 20 - "Vector Embedding & Storage"
Cohesion: 0.14
Nodes (16): embed_and_store_parent_child(), get_embedding_model(), get_vector_store(), Singleton. Downloads model on first call if not cached., Connects to Milvus standalone server with robust connection handling., Store parent-child chunks ke Chroma.      Strategy (Development):     - Child ch, detect_file_type(), Detect file type from extension. Raises ValueError if unsupported. (+8 more)

### Community 21 - "Admin Dashboard"
Cohesion: 0.26
Nodes (9): Table(), TableBody(), TableCaption(), TableCell(), TableFooter(), TableHead(), TableHeader(), TableRow() (+1 more)

### Community 22 - "Intent Classification"
Cohesion: 0.20
Nodes (12): classify_intent(), classify_intent_tiered(), classify_intent_with_llm(), Lightweight Intent Classifier — EnterpriseMind AI.  Tiered approach untuk menghe, LLM-based intent classification untuk query ambiguous.     Hanya dipanggil jika, Main entry point: Tiered classification.      Returns:         (intent, confiden, Tiered intent classification.      Returns:         (intent, confidence), _get_agents_for_intent() (+4 more)

### Community 23 - "Query Rewriting"
Cohesion: 0.23
Nodes (13): expand_query(), expand_query_dictionary(), expand_query_llm(), _load_abbreviations(), _load_synonyms(), need_query_expansion(), Query Rewriter — EnterpriseMind AI.  Decision tree untuk query expansion: 1. Dic, LLM-based expansion (~0.3s, $0.0001).     Hanya dipanggil untuk comprehensive/am (+5 more)

### Community 24 - "Message & Query DB"
Cohesion: 0.16
Nodes (11): fetch_one(), Fetch a single row as dict. Returns None if no rows., Any, Message CRUD operations — PostgreSQL., Save message to conversation history., save_message(), log_query(), Any (+3 more)

### Community 25 - "API Routes"
Cohesion: 0.18
Nodes (11): API Routes — EnterpriseMind AI.  Re-export routers for FastAPI include_router()., process_query(), BaseModel, Request, QueryRequest, QueryResponse, Query API — EnterpriseMind AI.  POST /api/query — Send question to multi-agent s, Process query through agent graph. Returns SSE stream. RBAC-aware. (+3 more)

### Community 26 - "MinIO Object Storage"
Cohesion: 0.19
Nodes (6): MinIOClient, MinIO storage client — EnterpriseMind AI. Replaces Google Drive client for local, Upload file to MinIO and return object_name., Download file from MinIO to local destination., Delete file from MinIO., Minio

### Community 27 - "User & Auth UI"
Cohesion: 0.19
Nodes (11): UsersPage(), LoginPage(), SideNavBar(), SideNavBarProps, Avatar(), AvatarBadge(), AvatarFallback(), AvatarGroup() (+3 more)

### Community 28 - "Auth API"
Cohesion: 0.24
Nodes (10): login(), LoginRequest, LoginResponse, logout(), BaseModel, Auth API — EnterpriseMind AI.  POST /api/auth/login  — Login with email + passwo, Login. Returns JWT token with RBAC fields. Sets HTTPOnly cookie., Logout — increment token_version to invalidate all previous tokens. (+2 more)

### Community 29 - "Sessions API"
Cohesion: 0.18
Nodes (11): delete_session(), get_session_messages(), list_sessions(), Sessions API — EnterpriseMind AI.  Endpoint untuk mengelola riwayat sesi chat pe, List semua sesi chat milik user yang login., Ambil semua pesan dalam satu sesi chat., Hapus sesi chat (beserta semua pesannya via CASCADE)., delete_user() (+3 more)

### Community 30 - "Users Admin API"
Cohesion: 0.23
Nodes (11): create_user(), CreateUserRequest, list_users(), BaseModel, Users API — EnterpriseMind AI.  CRUD endpoint untuk manajemen user oleh admin. H, List semua user dengan pagination. Hanya admin., Buat user baru. Hanya admin., Update user. Hanya admin. (+3 more)

### Community 31 - "Load Testing"
Cohesion: 0.17
Nodes (7): EnterpriseMindUser, Script load testing menggunakan Locust.  Cara menjalankan: 1. Pastikan backend u, Simulasi user mengirimkan kueri ke sistem multi-agent, Simulasi pengecekan status server, Simulasi user membuka daftar dokumen, Simulasi user membuka dashboard metrik, HttpUser

### Community 32 - "Knowledge Vault UI"
Cohesion: 0.26
Nodes (6): DocumentTable(), DocumentUploader(), CardDescription(), CardTitle(), Input(), Label()

### Community 33 - "Training Needs Analysis"
Cohesion: 0.23
Nodes (12): Business Issue, CCA (Core Competency Analysis), Organizational Learning Blueprint / Learning Focus, Competency Issue, DNA (Developmental Needs Analysis), Learning Roadmap, Pemangku Jabatan (Job Holders), Performance Issue (+4 more)

### Community 34 - "Verifier Agent"
Cohesion: 0.27
Nodes (8): _parse_verifier_response(), Verifier Agent — EnterpriseMind AI.  Fact-check retrieval results and calculate, Parse JSON from LLM response. Clamps confidence to 0-1., Verify document consistency and compute confidence score., run_verifier_agent(), invoke_with_retry(), LLM Provider — EnterpriseMind AI.  Groq provider — fast LPU inference. Dua model, Invoke LLM chain dengan retry untuk handle quota/rate limit errors.      Args:

### Community 35 - "Temporal Ingestion Workflow"
Cohesion: 0.22
Nodes (9): Upload document and start async ingestion via Temporal.     Returns 202 Accepted, upload_document(), get_temporal_client(), Temporal Client Helper — EnterpriseMind AI.  Helper functions for starting Tempo, Get or create Temporal client (singleton)., Start an ingestion workflow.      Returns:         workflow_id: Unique ID for tr, start_ingestion_workflow(), Client (+1 more)

### Community 36 - "Offline Evaluation"
Cohesion: 0.31
Nodes (7): compute_answer_contains(), compute_context_precision(), compute_recall_at_k(), print_summary(), Offline Evaluation Framework — EnterpriseMind AI.  Mengukur kualitas RAG system, run_evaluation(), run_query()

### Community 38 - "Chat Page"
Cohesion: 0.27
Nodes (5): ChatWindow(), ChatWindowProps, LoadingIndicator(), MessageBubble(), useChatStream()

### Community 39 - "Executor Agent"
Cohesion: 0.29
Nodes (6): _parse_executor_response(), Executor / Action Agent — EnterpriseMind AI.  Menghasilkan action items (to-do l, Parse JSON response dari Executor LLM., Generate action items untuk review manusia.      Args:         state: State Lang, run_executor_agent(), EnterpriseMind AI — Agents Package.  Agent logic. Routing hanya di graph/build_g

### Community 40 - "FastAPI Entry Point"
Cohesion: 0.25
Nodes (7): global_exception_handler(), health_check(), Request, EnterpriseMind AI — FastAPI Application Entry Point.  Entry point utama backend., Handler global untuk exception yang tidak tertangani.      Mengembalikan pesan e, Health check endpoint untuk monitoring., Exception

### Community 41 - "Temporal Package"
Cohesion: 0.29
Nodes (5): Temporal — EnterpriseMind AI.  Async document ingestion via Temporal.io. Provide, IngestionWorkflow, Temporal Workflow — EnterpriseMind AI.  Ingestion workflow that orchestrates doc, Document ingestion workflow with fault tolerance., timedelta

### Community 42 - "Web Search Tool"
Cohesion: 0.40
Nodes (5): Web Search Tool — EnterpriseMind AI.  Digunakan oleh agent untuk mencari informa, Bersihkan tag HTML, script, dan batasi panjang teks., Cari informasi di web menggunakan Tavily API.      Args:         query: Pertanya, _sanitize_content(), web_search()

### Community 43 - "Test Fixtures"
Cohesion: 0.40
Nodes (4): mock_llm(), mock_supabase(), Mock the Supabase client., Mock the LLM provider to return a deterministic AI message.

### Community 44 - "Calculator Tool"
Cohesion: 0.50
Nodes (3): calculate(), Calculator Tool — EnterpriseMind AI.  Digunakan untuk melakukan kalkulasi matema, Evaluasi ekspresi matematika sederhana secara aman.      Args:         expressio

## Knowledge Gaps
- **115 isolated node(s):** `backend`, `UserData`, `geist`, `metadata`, `$schema` (+110 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **18 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `build_agent_graph()` connect `LangGraph Agent Orchestration` to `Verifier Agent`, `RAGAS Evaluation Framework`, `Offline Evaluation`, `Executor Agent`, `Hybrid Retrieval Agent`, `Summarizer Agent`, `Intent Classification`, `API Routes`?**
  _High betweenness centrality (0.023) - this node is a cross-community bridge._
- **Why does `fetch_all()` connect `Metrics & Monitoring API` to `Temporal Workflow Activities`, `Documents API`, `Message & Query DB`, `API Routes`, `Sessions API`, `Users Admin API`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Why does `fetch_one()` connect `Message & Query DB` to `Documents API`, `Metrics & Monitoring API`, `Auth & Upload API`, `API Routes`, `Auth API`, `Sessions API`, `Users Admin API`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `build_agent_graph()` (e.g. with `run_executor_agent()` and `run_orchestrator_agent()`) actually correct?**
  _`build_agent_graph()` has 10 INFERRED edges - model-reasoned connections that need verification._
- **What connects `backend`, `UserData`, `geist` to the rest of the system?**
  _115 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Project Overview & Architecture` be split into smaller, more focused modules?**
  _Cohesion score 0.07562008469449485 - nodes in this community are weakly interconnected._
- **Should `Hybrid PDF/DOCX Extraction` be split into smaller, more focused modules?**
  _Cohesion score 0.080338266384778 - nodes in this community are weakly interconnected._