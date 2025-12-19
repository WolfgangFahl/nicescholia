from dataclasses import dataclass

import nscholia


@dataclass
class Version:
    """
    Version handling for nicescholia
    """

    name = "nicescholia"
    version = nscholia.__version__
    date = "2025-12-17"
    updated = "2025-12-19"
    description = "nicegui based scholia"
    authors = "Wolfgang Fahl"
    doc_url = "https://wiki.bitplan.com/index.php/nicescholia"
    chat_url = "https://github.com/WolfgangFahl/nicescholia/discussions"
    cm_url = "https://github.com/WolfgangFahl/nicescholia"
    license = """Copyright 2025 contributors. All rights reserved.

  Licensed under the Apache License 2.0
  http://www.apache.org/licenses/LICENSE-2.0

  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied."""

    longDescription = f"""{name} version {version}
{description}

  Created by {authors} on {date} last updated {updated}"""
