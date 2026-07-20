# Sample run — general research (text-only, no chart)

A real captured run on a **non-CX, text-only** query — demonstrating the system is
domain-neutral and works without a visual input (the plan decomposes, parallel research +
critic validation run as usual, the writer streams a cited answer).

---

## Input
> What are the main causes of high latency in retrieval-augmented generation (RAG) systems, and
> what are the recommended mitigations?

## Output

High latency in retrieval-augmented generation (RAG) systems stems from several distinct phases,
including embedding generation, vector search, LLM processing, and orchestration overhead.

**Retrieval-phase latency**
The initial retrieval phase introduces latency through both query embedding and vector database
operations:
- **Embedding generation:** Generating embeddings is a high-latency step due to the compute-intensive
  forward pass required by transformer models (source). This can be mitigated by using specialized
  servers like Hugging Face Text Embeddings Inference (TEI) that optimize kernels and batching
  (source).
- **Vector-search complexity:** Higher vector dimensionality increases latency by placing greater
  compute and memory pressure on distance calculations (source). Recommended mitigations include:
  - *Indexing:* Using HNSW indexing provides lower query latency than IVF alternatives (source).
  - *Compression:* Scalar and Product Quantization reduce latency by compressing vectors (source),
    while Matryoshka Representation Learning (MRL) allows for vector truncation without requiring
    model retraining (source).

**Generation-phase latency**
The LLM generation phase is often the most significant bottleneck:
- **Prefill latency (time to first token):** Large context windows and high volumes of retrieved
  documents increase prefill latency because the model must process all input tokens at once to
  build the KV cache (source). Prefix caching can skip this computation for static or repeated
  documents (source).
- **Decoding latency:** Memory bandwidth is the primary bottleneck for decoding (source).
  Mitigations include:
  - *Quantization:* Using 4-bit precision reduces memory bandwidth usage to improve speed (source).
  - *Speculative decoding:* Uses a smaller "draft" model to predict tokens, which are then verified
    in parallel by the target model, yielding 2×–4× speedups (source). Retrieval-Augmented
    Speculative Decoding (RASD) specifically uses the retrieved context to improve draft accuracy
    (source).
  - *Limits:* Applying maximum output-token limits (`max_tokens`) reduces system-wide queueing
    delays (source).

**Orchestration and system mitigations**
System-level steps such as re-ranking and pre-processing also contribute to total turnaround time:
- **Re-ranking costs:** Cross-encoder re-ranking typically adds 100–400 ms to retrieval latency, or
  roughly 18 ms per document (source). A two-stage retrieval approach is recommended to balance
  quality and speed (source).
- **Semantic caching:** Reusing responses for semantically similar requests can improve average
  latency by up to 88% (source). While it introduces a small ~20 ms overhead for lookups, the
  overall saving is significant (source).
- **Parallelization and streaming:** Parallelizing orchestration steps can reduce pre-processing
  latency by up to 57% (source). For user-facing applications, streaming responses mitigates
  perceived latency by aiming for a Time to First Token (TTFT) of less than 1 second (source).

**Sources**
1. Embedding generation is a high-latency phase in RAG caused by the compute-intensive forward pass of transformer models. — milvus.io
2. Inference latency can be mitigated using specialized servers like Hugging Face TEI that optimize batching and kernels. — discuss.huggingface.co
3. Higher vector dimensionality increases search latency by placing greater compute and memory pressure on the system during distance calculations. — milvus.io
4. HNSW indexing provides lower query latency than IVF at the cost of higher memory usage. — bigdataboutique.com
5. Matryoshka Representation Learning (MRL) enables latency reduction by allowing vector truncation without retraining. — weaviate.io
6. Quantization techniques like Scalar and Product Quantization reduce latency by compressing vectors to lower-precision formats. — arxiv.org
7. Large context windows and a high number of retrieved documents increase prefill latency (Time to First Token) because the model must process all input tokens at once to build the KV cache. — www.spheron.network
8. Model quantization techniques like 4-bit precision reduce memory bandwidth usage, which is the primary bottleneck for LLM decoding latency, enabling significant speed improvements. — latitude.so
9. Speculative decoding provides 2x to 4x inference speedups by utilizing a smaller draft model to guess tokens which are then verified in parallel by the target model. — www.bentoml.com
10. Retrieval-Augmented Speculative Decoding (RASD) specifically optimizes RAG by using retrieval context to increase draft model accuracy and generation throughput. — arxiv.org
11. Applying maximum output token limits (max_tokens) can significantly reduce system-wide queueing delays and end-to-end request latency. — arxiv.org
12. Prefix caching optimizes RAG latency by storing KV caches for static or repeated retrieved documents, skipping the costly prefill computation phase. — arxiv.org
13. Cross-encoder re-ranking typically adds 100–400ms to retrieval latency but can reduce total end-to-end latency by optimizing the context sent to the LLM. — particula.tech
14. The latency of cross-encoder re-ranking is roughly 18ms per document, necessitating a two-stage retrieval approach to maintain acceptable performance. — quartalis.co.uk
15. Semantic caching can improve average end-to-end RAG latency by up to 88% by reusing responses for semantically similar requests. — aws.amazon.com
16. Semantic cache lookups introduce a small overhead of approximately 20ms due to embedding generation and vector similarity search. — ndeplace.medium.com
17. Streaming responses mitigate perceived latency by aiming for a Time to First Token (TTFT) of less than 1 second. — www.reddit.com
18. Parallelization of orchestration steps can reduce pre-processing latency by as much as 57%. — dl.acm.org
