# PAR architecture diagrams

Source diagrams are authored in **Mermaid** (`*.mmd`). A rendered **PNG** accompanies
each one.

| Diagram | Source | PNG | Shows |
|---|---|---|---|
| Layering | `01-layering.mmd` | `01-layering.png` | Where PAR sits: core specs → evidence layer (PAR) → attestation surface → scoring |
| Mint / verify | `02-mint-verify.mmd` | `02-mint-verify.png` | A settled AP2 mandate becomes a VIR, then is verified |
| Settlement states | `03-settlement-states.mmd` | `03-settlement-states.png` | pending → settled → active, with refund/chargeback invalidation |
| Operator independence | `04-independence.mmd` | `04-independence.png` | Diverse operator vs. reciprocal self-dealing pair |

## Rendering

To regenerate from the Mermaid sources with the official renderer:

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc -i 01-layering.mmd -o 01-layering.png -s 2
```

The committed PNGs in this folder were produced with **Graphviz** (`*.dot` + `dot -Tpng`)
because the Mermaid CLI requires a headless Chromium that was not available in the
build environment. The `.mmd` files remain the canonical, portable source and render
directly on GitHub and in most Markdown editors.
