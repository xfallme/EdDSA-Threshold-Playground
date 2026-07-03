# EdDSA Threshold Playground

> Interactive browser-based playgrounds for exploring **EdDSA** and **FROST threshold signatures**, powered by **PyScript** and running entirely in the browser.

<p align="center">
  <a target="_blank" href="https://xfallme.github.io/EdDSA-Threshold-Playground/playground-eddsa.html">
    <img alt="EdDSA Playground" src="https://img.shields.io/badge/Launch-EdDSA%20Playground-2563eb?style=for-the-badge">
  </a>
  &nbsp;
  <a target="_blank" href="https://xfallme.github.io/EdDSA-Threshold-Playground/playground-frost.html">
    <img alt="FROST Playground" src="https://img.shields.io/badge/Launch-FROST%20Playground-16a34a?style=for-the-badge">
  </a>
</p>

---

## What is this?

This repository contains interactive demonstrations of the educational **[EdDSA-Threshold](https://github.com/xfallme/EdDSA-Threshold)** implementation.

Everything runs **client-side** using **PyScript**, meaning no backend or server-side cryptography is required. The playgrounds are intended for learning, experimentation, and visualizing the algorithms. Not for production use.

---

## Playgrounds

### 🔐 EdDSA Playground

Explore the EdDSA signature scheme interactively.

Features:

- Generate key pairs
- Sign arbitrary messages
- Verify arbitrary signatures
- Experiment with Ed25519 and Ed448 (and their variants)

➡️ **Open:** [playground-eddsa.html](./playground-eddsa.html)

---

### 👥 FROST Playground

Visualize and experiment with threshold signatures.

Features:

- Create threshold groups
- Generate secret shares
- Simulate signing rounds (you are in control of all participants)
- Aggregate partial signatures
- Verify the final signature

➡️ **Open:** [playground-frost.html](./playground-frost.html)

---

## Related Projects

- **EdDSA-Threshold Library:** [https://github.com/xfallme/EdDSA-Threshold/](https://github.com/xfallme/EdDSA-Threshold/)
- **EdDSA-Threshold Package:** [https://pypi.org/project/eddsa-threshold/](https://pypi.org/project/eddsa-threshold/)

---

## Disclaimer

This project is intended for **educational purposes only**.

It demonstrates the algorithms and protocol flow behind EdDSA and FROST.
It has **not** been audited and **must not** be used to protect real-world secrets or assets.