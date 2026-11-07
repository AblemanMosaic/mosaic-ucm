# Semantic passage protocol

This protocol reserves a stable integration point for CSIL, GTK, and GCNL without claiming those providers already exist in UCM.

The original UTF-8 text is immutable. An annotation identifies exact UTF-8 byte spans and offers qualified candidates: vocabulary root, integer term ID, integer sense ID, and bound term. Ambiguity produces a clarification request. The model or user selects candidates by qualified integers. Bounded outcomes are resolved, clarification required, or budget exhausted.

A reading view displays the original prose. Integer, split, and audit views add rooted annotations. Annotation never silently rewrites the text. `REFERENCE_UNBOUND` discloses that no provider is pinned; `PINNED_EXTERNAL_PROVIDER` binds the provider root.

