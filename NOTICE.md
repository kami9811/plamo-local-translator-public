# Notices and license boundaries

**Built with PLaMo.** This is an independent, unofficial application. It is not affiliated with, endorsed by, or maintained by Preferred Networks (PFN), Google, IBM, or DeepL.

## Application code

Original application code, scripts, original example inputs, and documentation written for this project are provided under the MIT License in `LICENSE`. This grant does not replace the licenses or contractual conditions of third-party materials.

## PLaMo models and generated content

PLaMo 3 Translate models are provided by Preferred Networks under the PLaMo Community License Agreement. Model weights, tokenizers, CUDA, Node.js and llama.cpp binaries are **not bundled** in this repository or extension ZIP. The setup script downloads official distributions separately.

PLaMo-generated translation text in `samples/handoff.json`, `samples/handoff.md`, `docs/benchmarks.json`, other generated translation fields in `docs/validation-evidence/`, and the translation portions of screenshots is identified as model output and is provided subject to the PLaMo Community License Agreement. These generated parts are not relicensed as MIT by the application license. Copies of the agreement are included in `licenses/PLaMo-Community-License-ja.txt` and `licenses/PLaMo-Community-License-en.txt`. Exported review JSON/Markdown also carries attribution and agreement copies.

For commercial model use, the agreement includes prior registration and a revenue/sales threshold. Product/service development or provision and organizational use are included in its definition of commercial purpose. The software's MIT license does not waive these conditions. Please read the agreement and consult PFN about your intended use if the classification is unclear.

Model downloads require the explicit `--accept-model-license` option. This acknowledges model terms; it does not perform commercial registration or acquire a separate commercial license.

## Other dependencies

- llama.cpp: MIT; downloaded separately from the official ggml-org repository.
- Node.js and the CUDA runtime: downloaded separately; their distribution includes its own license notices.
- TypeScript and Playwright: Apache-2.0.
- esbuild and Chrome type definitions: MIT.
- axe-core and @axe-core/playwright: MPL-2.0, used for development accessibility checks.

Installed development-package license/notice copies and exact versions are listed in `licenses/dependencies.json`. These tools are not application runtime imports. Their original terms remain in effect.

Material 3 Expressive and Carbon inform the original CSS and interaction design. Their logos, fonts, branded assets, or component libraries are not redistributed as application assets. No certification or complete design-system conformity is claimed.
