# S115 — Exact reference-edge coverage (design v8)

Status: frozen after the second adversarial review and before procedure-novelty
implementation. Local shadow only. Active config remains
`config/reference_edge_contract_v4.yaml`, SHA256
`2dab22ba5b324e5ad42709aa0d6a8638a3b80b25d03eae7667fa3b3ad229823c`.

This version inherits v5-v7. It closes the remaining canonical-delta defect:
product/UI/numeric tokens co-occurring with a procedure verb cannot make the same
already-served action novel.

Procedure atoms are now independent:

1. inflected action words map to a generic action family (`press`, `select`,
   `enter`, `connect`, `configure`, `adjust`, `change`, `remove`, `reinstall`,
   `use`);
2. the canonical action signal contains only that family; the fixed query and
   same-unit object/attribute contract supply the obligation binding;
3. structured codes and numeric values become separate `procedure_code` or
   `procedure_value` atoms only in a multi-cell Markdown table row that also
   contains an explicit action;
4. prose identifiers such as a product code or `IP` cannot decorate an action
   signal and manufacture novelty.

Thus a source that already says “configure WiFi/IP” is not augmented by a card
that merely repeats “configure IP for MODEL-X”. A procedural table can still add
exact display states such as renamed synthetic codes, V01 or V02, each compared
independently against served atoms.

No manufacturer, product, QID, expected value or labelled diagnostic vocabulary
is introduced. The nested holdout SHA256
`107e5f0f0ec27117a4f9cec180169dbb43aad2ee385e31fbc8f0eeb3282c297e`
remains sealed and all prior invalidation rules remain in force.
