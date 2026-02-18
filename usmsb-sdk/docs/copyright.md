# USMSB SDK Copyright and License Notice

**Universal System Model of Social Behavior - Intellectual Property and Licensing**

Last Updated: February 2025

---

## Table of Contents

1. [Copyright Notice](#1-copyright-notice)
2. [License Overview](#2-license-overview)
3. [Apache License 2.0](#3-apache-license-20)
4. [Third-Party Components](#4-third-party-components)
5. [USMSB Model License](#5-usmsb-model-license)
6. [Trademark Notice](#6-trademark-notice)
7. [Patent Notice](#7-patent-notice)
8. [Attribution Requirements](#8-attribution-requirements)
9. [Contributions](#9-contributions)
10. [Contact Information](#10-contact-information)

---

## 1. Copyright Notice

### 1.1 Primary Copyright

Copyright (c) 2024-2025 [Company Name]. All rights reserved.

The USMSB SDK, including all source code, documentation, and related materials, is protected by copyright laws and international treaty provisions.

### 1.2 Scope of Copyright

The following are copyrighted by [Company Name]:

- USMSB SDK source code
- API implementations
- Documentation and guides
- Sample code and examples
- Test suites and benchmarks
- Build scripts and configurations
- Website content
- Logos and visual designs

### 1.3 Copyright Symbol

Where applicable, the following notice should be displayed:

```
Copyright (c) 2024-2025 [Company Name]. Licensed under the Apache License, Version 2.0.
```

---

## 2. License Overview

### 2.1 Open Source License

USMSB SDK is released under the **Apache License 2.0**, a permissive open-source license that allows:

| Right | Description |
|-------|-------------|
| **Commercial Use** | Use in commercial applications |
| **Modification** | Modify and create derivatives |
| **Distribution** | Distribute copies and derivatives |
| **Private Use** | Use privately without distribution |
| **Patent Grant** | Patent license from contributors |

### 2.2 License Comparison

| Feature | Apache 2.0 | MIT | GPL v3 |
|---------|------------|-----|--------|
| Copyleft | No | No | Yes |
| Patent Grant | Yes | No | Yes |
| Attribution Required | Yes | Yes | Yes |
| Trademark Use | No | No | No |
| Liability Disclaimer | Yes | Yes | Yes |

### 2.3 Why Apache 2.0?

We chose Apache License 2.0 because:
- Permissive for commercial adoption
- Clear patent grant provisions
- Compatible with many other licenses
- Widely recognized and trusted
- Supports open ecosystem growth

---

## 3. Apache License 2.0

### 3.1 Full License Text

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work.

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof.

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License.

      Subject to the terms and conditions of this License, each Contributor
      hereby grants to You a perpetual, worldwide, non-exclusive, no-charge,
      royalty-free, irrevocable copyright license to reproduce, prepare
      Derivative Works of, publicly display, publicly perform, sublicense,
      and distribute the Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License.

      Subject to the terms and conditions of this License, each Contributor
      hereby grants to You a perpetual, worldwide, non-exclusive, no-charge,
      royalty-free, irrevocable (except as stated in this section) patent
      license to make, have made, use, offer to sell, sell, import, and
      otherwise transfer the Work.

   4. Redistribution.

      You may reproduce and distribute copies of the Work or Derivative Works
      thereof in any medium, with or without modifications, and in Source or
      Object form, provided that You meet the following conditions:

      (a) You must give any other recipients of the Work or Derivative Works
          a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works that
          You distribute, all copyright, patent, trademark, and attribution
          notices from the Source form of the Work; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file.

   5. Submission of Contributions.

      Unless You explicitly state otherwise, any Contribution intentionally
      submitted for inclusion in the Work by You to the Licensor shall be
      under the terms and conditions of this License, without any additional
      terms or conditions.

   6. Trademarks.

      This License does not grant permission to use the trade names,
      trademarks, service marks, or product names of the Licensor.

   7. Disclaimer of Warranty.

      Unless required by applicable law or agreed to in writing, Licensor
      provides the Work on an "AS IS" BASIS, WITHOUT WARRANTIES OR
      CONDITIONS OF ANY KIND.

   8. Limitation of Liability.

      In no event shall Licensor be liable for any damages arising from
      the use of the Work.

   9. Accepting Warranty or Additional Liability.

      While redistributing the Work or Derivative Works thereof, You may
      choose to offer support, warranty, indemnity, or other liability
      obligations and/or rights consistent with this License.
```

### 3.2 Summary of Rights and Obligations

#### You CAN:
- Use the software for any purpose
- Study and modify the software
- Distribute copies of the software
- Distribute modified versions
- Use in proprietary software
- Use in commercial products

#### You MUST:
- Include a copy of the Apache License
- Keep copyright notices intact
- State changes to files
- Include NOTICE file if present

#### You CANNOT:
- Use our trademarks without permission
- Hold contributors liable
- Remove license or copyright notices

---

## 4. Third-Party Components

### 4.1 Included Dependencies

USMSB SDK includes or depends on the following third-party components:

| Component | Version | License | Purpose |
|-----------|---------|---------|---------|
| Python | 3.9+ | PSF License | Runtime |
| FastAPI | 0.100+ | MIT | REST API |
| Pydantic | 2.0+ | MIT | Data validation |
| SQLAlchemy | 2.0+ | MIT | ORM |
| Redis | - | BSD | Caching |
| httpx | 0.24+ | BSD | HTTP client |
| openai | 1.0+ | MIT | OpenAI adapter |
| anthropic | 0.18+ | MIT | Claude adapter |
| google-generativeai | 0.3+ | Apache 2.0 | Gemini adapter |
| langchain | 0.1+ | MIT | Agentic framework |

### 4.2 Third-Party License Texts

Third-party license texts are included in the `LICENSES/` directory:

```
LICENSES/
├── Apache-2.0.txt
├── MIT.txt
├── BSD-3-Clause.txt
├── PSF-2.0.txt
└── ...
```

### 4.3 Dependency Updates

We regularly update dependencies for:
- Security patches
- Bug fixes
- Feature updates
- Compatibility

---

## 5. USMSB Model License

### 5.1 Theoretical Framework

The USMSB (Universal System Model of Social Behavior) theoretical framework is also licensed under Apache License 2.0, including:

- Nine Core Elements definitions
- Nine Universal Action Interfaces
- Six Core Logic patterns
- Theoretical documentation

### 5.2 Academic Use

For academic and research use:
- Proper attribution is required
- Citation format provided below
- No additional restrictions

### 5.3 Citation Format

When referencing USMSB in academic work:

```
@software{usmsb_sdk_2025,
  author = {{USMSB SDK Team}},
  title = {USMSB SDK: Universal System Model of Social Behavior},
  year = {2025},
  url = {https://github.com/usmsb/sdk}
}
```

### 5.4 Attribution in Derivatives

If you create derivative works based on the USMSB model:
- Acknowledge the original work
- Include reference to USMSB SDK
- Do not imply endorsement

---

## 6. Trademark Notice

### 6.1 Registered Trademarks

The following are trademarks or registered trademarks of [Company Name]:

- "USMSB"
- "USMSB SDK"
- "Universal System Model of Social Behavior"
- The USMSB logo
- Other service marks and logos

### 6.2 Trademark Usage Guidelines

#### Allowed Usage
- Descriptive references to USMSB SDK
- Linking to official resources
- Accurate descriptions of compatibility

#### Prohibited Usage
- Use in product names without permission
- Implying endorsement or affiliation
- Modifying trademarks
- Using confusingly similar marks

### 6.3 Logo Usage

The USMSB logo may be used:
- To indicate compatibility with USMSB SDK
- In documentation linking to USMSB
- With prior written permission

The USMSB logo may NOT be used:
- As your application's icon
- In a modified form
- To imply partnership without agreement

### 6.4 Third-Party Trademarks

Third-party trademarks mentioned in our software:
- Are property of their respective owners
- Are used for identification purposes only
- Do not imply endorsement

---

## 7. Patent Notice

### 7.1 Patent Grant

Under Apache License 2.0, contributors grant a patent license for any patents they hold that are necessary to use the software.

### 7.2 Patent Retaliation

The patent license terminates if you institute patent litigation against contributors alleging the software constitutes patent infringement.

### 7.3 Patent Disclaimer

We make no representations regarding patent coverage:
- Software may be covered by third-party patents
- Use at your own risk
- Consult legal counsel for patent advice

---

## 8. Attribution Requirements

### 8.1 Required Attribution

When using USMSB SDK, include the following attribution:

```
This software includes USMSB SDK.
Copyright (c) 2024-2025 [Company Name].
Licensed under the Apache License, Version 2.0.
https://github.com/usmsb/sdk
```

### 8.2 NOTICE File

If redistributing, include the NOTICE file content:

```
USMSB SDK
Copyright 2024-2025 [Company Name]

This product includes software developed by the USMSB SDK Team.

This product includes software developed at:
- The Apache Software Foundation (https://www.apache.org/)
- FastAPI (https://fastapi.tiangolo.com/)
- Pydantic (https://pydantic-docs.helpmanual.io/)

[Additional third-party attributions as applicable]
```

### 8.3 Source Code Header

Each source file should include:

```python
# Copyright 2024-2025 [Company Name]
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

---

## 9. Contributions

### 9.1 Contributor License Agreement

All contributors must sign our Contributor License Agreement (CLA):
- Individual CLA for personal contributions
- Corporate CLA for employer-covered contributions

### 9.2 Submission Terms

By submitting contributions, you:
- Grant copyright license under Apache 2.0
- Grant patent license under Apache 2.0
- Confirm you have the right to grant these licenses
- Agree contributions are original work

### 9.3 Contribution Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Sign the CLA (automated)
5. Submit a pull request
6. Address review feedback

### 9.4 Code of Conduct

All contributors must follow our Code of Conduct:
- Be respectful and inclusive
- Welcome diverse perspectives
- Accept constructive criticism
- Focus on community benefit

---

## 10. Contact Information

### 10.1 Legal Inquiries

For legal and licensing questions:
- Email: legal@usmsb-sdk.io
- Address: [Company Address]

### 10.2 Trademark Requests

For trademark licensing:
- Email: trademarks@usmsb-sdk.io
- Include intended use details

### 10.3 Security Issues

For security vulnerabilities:
- Email: security@usmsb-sdk.io
- Do not disclose publicly until fixed
- Follow responsible disclosure practices

### 10.4 General Questions

For general questions:
- Email: info@usmsb-sdk.io
- GitHub Issues: github.com/usmsb/sdk/issues
- Community: community.usmsb-sdk.io

---

## Appendix A: Full License Text Location

The complete Apache License 2.0 text is available at:

- **In the repository**: `LICENSE` file
- **Online**: http://www.apache.org/licenses/LICENSE-2.0
- **SPDX identifier**: `Apache-2.0`

---

## Appendix B: Frequently Asked Questions

### Q: Can I use USMSB SDK in my commercial product?

**A:** Yes. Apache License 2.0 permits commercial use without restrictions.

### Q: Do I need to open source my application?

**A:** No. Apache License 2.0 does not require you to license your application under any particular terms.

### Q: Can I modify USMSB SDK?

**A:** Yes. You can modify the SDK, but you must:
- Keep the original license and copyright notices
- Indicate your changes
- Include the original NOTICE file if present

### Q: Do I need to attribute USMSB SDK?

**A:** Yes. You must include:
- Copy of the Apache License
- Original copyright notices
- NOTICE file content (if applicable)

### Q: Can I use the USMSB name/logo?

**A:** Limited use is permitted to indicate compatibility. For other uses, contact us for permission.

### Q: What if I find a patent issue?

**A:** Consult with legal counsel. The license includes a patent grant from contributors but not from third parties.

---

## Appendix C: License Compatibility

USMSB SDK (Apache 2.0) is compatible with:

| License | Compatibility |
|---------|---------------|
| MIT | Yes |
| BSD-2-Clause | Yes |
| BSD-3-Clause | Yes |
| Apache 2.0 | Yes |
| LGPL-2.1 | Yes |
| LGPL-3.0 | Yes |
| GPL-2.0 | Yes (combined work must be GPL-2.0) |
| GPL-3.0 | Yes (combined work must be GPL-3.0) |
| AGPL-3.0 | Yes (combined work must be AGPL-3.0) |

---

**Document Information**

- **Version**: 1.0.0
- **Last Updated**: February 2025
- **Author**: USMSB SDK Legal Team

---

*This document is provided for informational purposes. The actual license terms are defined in the LICENSE file included with the software.*
