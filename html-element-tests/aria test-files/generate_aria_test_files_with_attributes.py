import os

roles_attributes = {
    "checkbox": {
        "required": ["aria-checked"],
        "allowed": ["aria-checked", "aria-disabled", "aria-readonly", "aria-required"],
        "values": {
            "aria-checked": ["true", "false", "mixed"]
        }
    },
    "gridcell": {
        "required": [],
        "allowed": ["aria-colindex", "aria-colspan", "aria-rowindex", "aria-rowspan", "aria-selected"],
        "values": {
            "aria-selected": ["true", "false"]
        }
    },
    "link": {
        "required": [],
        "allowed": ["aria-disabled", "aria-expanded", "aria-haspopup"],
        "values": {
            "aria-expanded": ["true", "false"]
        }
    },
    "menuitem": {
        "required": [],
        "allowed": ["aria-checked", "aria-disabled", "aria-haspopup", "aria-posinset", "aria-setsize"],
        "values": {
            "aria-checked": ["true", "false", "mixed"]
        }
    },
    "menuitemcheckbox": {
        "required": ["aria-checked"],
        "allowed": ["aria-checked", "aria-disabled", "aria-posinset", "aria-setsize"],
        "values": {
            "aria-checked": ["true", "false", "mixed"]
        }
    },
    "menuitemradio": {
        "required": ["aria-checked"],
        "allowed": ["aria-checked", "aria-disabled", "aria-posinset", "aria-setsize"],
        "values": {
            "aria-checked": ["true", "false"]
        }
    },
    "option": {
        "required": [],
        "allowed": ["aria-checked", "aria-disabled", "aria-posinset", "aria-selected", "aria-setsize"],
        "values": {
            "aria-selected": ["true", "false"]
        }
    },
    "progressbar": {
        "required": ["aria-valuemax", "aria-valuemin", "aria-valuenow"],
        "allowed": ["aria-valuemax", "aria-valuemin", "aria-valuenow", "aria-valuetext"]
    },
    "radio": {
        "required": ["aria-checked"],
        "allowed": ["aria-checked", "aria-disabled", "aria-posinset", "aria-readonly", "aria-required", "aria-setsize"],
        "values": {
            "aria-checked": ["true", "false"]
        }
    },
    "scrollbar": {
        "required": ["aria-valuemax", "aria-valuemin", "aria-valuenow"],
        "allowed": ["aria-orientation", "aria-valuemax", "aria-valuemin", "aria-valuenow", "aria-valuetext"],
        "values": {
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "searchbox": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-autocomplete", "aria-disabled", "aria-expanded", "aria-haspopup", "aria-multiline", "aria-placeholder", "aria-readonly", "aria-required"],
        "values": {
            "aria-autocomplete": ["both", "inline", "list", "none"],
            "aria-expanded": ["true", "false"]
        }
    },
    "separator": {
        "required": [],
        "allowed": ["aria-orientation"],
        "values": {
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "slider": {
        "required": ["aria-valuemax", "aria-valuemin", "aria-valuenow"],
        "allowed": ["aria-orientation", "aria-valuemax", "aria-valuemin", "aria-valuenow", "aria-valuetext"],
        "values": {
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "spinbutton": {
        "required": ["aria-valuemax", "aria-valuemin", "aria-valuenow"],
        "allowed": ["aria-valuemax", "aria-valuemin", "aria-valuenow", "aria-valuetext", "aria-required"]
    },
    "switch": {
        "required": ["aria-checked"],
        "allowed": ["aria-checked", "aria-disabled", "aria-readonly", "aria-required"],
        "values": {
            "aria-checked": ["true", "false"]
        }
    },
    "tab": {
        "required": [],
        "allowed": ["aria-disabled", "aria-expanded", "aria-posinset", "aria-selected", "aria-setsize"],
        "values": {
            "aria-expanded": ["true", "false"],
            "aria-selected": ["true", "false"]
        }
    },
    "tabpanel": {
        "required": [],
        "allowed": ["aria-expanded"],
        "values": {
            "aria-expanded": ["true", "false"]
        }
    },
    "textbox": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-autocomplete", "aria-disabled", "aria-expanded", "aria-haspopup", "aria-multiline", "aria-placeholder", "aria-readonly", "aria-required"],
        "values": {
            "aria-autocomplete": ["both", "inline", "list", "none"],
            "aria-expanded": ["true", "false"]
        }
    },
    "treeitem": {
        "required": [],
        "allowed": ["aria-checked", "aria-disabled", "aria-expanded", "aria-haspopup", "aria-level", "aria-posinset", "aria-selected", "aria-setsize"],
        "values": {
            "aria-checked": ["true", "false", "mixed"],
            "aria-expanded": ["true", "false"]
        }
    },
    "combobox": {
        "required": ["aria-controls", "aria-expanded"],
        "allowed": ["aria-activedescendant", "aria-autocomplete", "aria-controls", "aria-expanded", "aria-required"],
        "values": {
            "aria-expanded": ["true", "false"],
            "aria-autocomplete": ["both", "inline", "list", "none"]
        }
    },
    "grid": {
        "required": [],
        "allowed": ["aria-level", "aria-multiselectable", "aria-readonly"],
        "values": {
            "aria-multiselectable": ["true", "false"],
            "aria-readonly": ["true", "false"]
        }
    },
    "listbox": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-disabled", "aria-multiselectable", "aria-orientation", "aria-readonly", "aria-required"],
        "values": {
            "aria-multiselectable": ["true", "false"],
            "aria-orientation": ["horizontal", "vertical"],
            "aria-readonly": ["true", "false"]
        }
    },
    "menu": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-disabled", "aria-expanded", "aria-haspopup", "aria-orientation"],
        "values": {
            "aria-expanded": ["true", "false"],
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "menubar": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-disabled", "aria-orientation"],
        "values": {
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "radiogroup": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-disabled", "aria-orientation", "aria-readonly", "aria-required"],
        "values": {
            "aria-orientation": ["horizontal", "vertical"],
            "aria-readonly": ["true", "false"]
        }
    },
    "tablist": {
        "required": [],
        "allowed": ["aria-level", "aria-multiselectable", "aria-orientation"],
        "values": {
            "aria-multiselectable": ["true", "false"],
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "tree": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-multiselectable", "aria-orientation", "aria-required"],
        "values": {
            "aria-multiselectable": ["true", "false"],
            "aria-orientation": ["horizontal", "vertical"]
        }
    },
    "treegrid": {
        "required": [],
        "allowed": ["aria-activedescendant", "aria-level", "aria-multiselectable", "aria-orientation", "aria-readonly", "aria-required"],
        "values": {
            "aria-multiselectable": ["true", "false"],
            "aria-orientation": ["horizontal", "vertical"],
            "aria-readonly": ["true", "false"]
        }
    }
}

template = """<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>test file: {role} role</title>
    <link rel="stylesheet" href="../style/styles.css">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <style>
        [tabindex="0"]:focus {{
            outline: 2px solid blue;
        }}
    </style>
</head>
<body>
    <h1>
        <code>{role}</code> role
    </h1>

    <div class="meta">
        <div class="criteria">
            <h2>
                Pass Criteria
            </h2>
            <ul id="criteria-list">
                <li id="basic-criteria">#1: Element is supported</li>
                <li>#2: Correct HTML and Core Accessibility API mappings</li>
                <li>#3: Correct Accessible Name &amp; Description Calculation</li>
            </ul>
        </div>

        <div class="reference">
            <h2>
                Reference
            </h2>
            <ul>
                <li>
                    <a href="https://www.w3.org/TR/wai-aria-1.1/#{role}">WAI-ARIA <code>{role}</code> role</a>
                </li>
                <li>
                    <a href="https://w3c.github.io/aria-practices/#{role}">ARIA Authoring Practices for <code>{role}</code> role</a>
                </li>
                <li>
                    <a href="https://www.w3.org/TR/core-aam-1.1/#role-map-{role}">Core Accessibility API Mappings for <code>{role}</code> role</a>
                </li>
            </ul>
        </div>
    </div>

    {tests}

    <script src="../scripts/test-scripts.js"></script>
    <script>
        var test = [];
        var el = document.getElementById('{role}-01');
        var isSupported = (el instanceof HTMLElement && !(el instanceof HTMLUnknownElement));

        test.push({{id: "basic-criteria", pass: isSupported}});
        displaySupportResults(test);
        
        // Script to cycle through multiple values for states and properties
        var elements = document.querySelectorAll('[id^={role}]');
        elements.forEach(function(el) {{
            el.addEventListener('click', function() {{
                {cycling_logic}
            }});
            el.addEventListener('keypress', function(event) {{
                if (event.key === 'Enter' || event.key === ' ') {{
                    {cycling_logic}
                }}
            }});
        }});
    </script>
</body>
</html>
"""

test_case_template = """
<div class="test">
    <h2 class="test-title" id="{role}-{index:03d}">
        Test {role}-{index:03d}: <code>{role}</code> role, {description}
    </h2>
    <div class="test-case">
        <div role="{role}" id="{role}-{index:02d}" {attributes}>{role}-{index:02d}: {attr_value}</div>
    </div>
</div>
"""

cycling_logic_template = """
var currentVal = el.getAttribute('{attr}');
var values = {cycling_values};
var nextVal = values[(values.indexOf(currentVal) + 1) % values.length];
el.setAttribute('{attr}', nextVal);
el.textContent = el.id + ': ' + nextVal;
"""

output_dir = "aria_test_files"
os.makedirs(output_dir, exist_ok=True)

for role, attrs in roles_attributes.items():
    tests = ""
    index = 1
    cycling_logic_parts = []

    # Adding required attributes tests
    if attrs["required"]:
        for attr in attrs["required"]:
            description = f"with required attribute {attr}"
            if attr in attrs.get("values", {}):
                value = attrs["values"][attr][0]
                attributes = f'{attr}="{value}" tabindex="0"'
                cycling_values = attrs["values"][attr]
                cycling_logic_parts.append(cycling_logic_template.format(attr=attr, cycling_values=cycling_values))
            else:
                attributes = f'{attr}="true" tabindex="0"'
                value = "true"
            tests += test_case_template.format(role=role, index=index, description=description, attributes=attributes, attr_value=value)
            index += 1

    # Adding allowed attributes tests
    for attr in attrs["allowed"]:
        description = f"with allowed attribute {attr}"
        if attr in attrs.get("values", {}):
            value = attrs["values"][attr][0]
            attributes = f'{attr}="{value}" tabindex="0"'
            cycling_values = attrs["values"][attr]
            cycling_logic_parts.append(cycling_logic_template.format(attr=attr, cycling_values=cycling_values))
        else:
            attributes = f'{attr}="true" tabindex="0"'
            value = "true"
        tests += test_case_template.format(role=role, index=index, description=description, attributes=attributes, attr_value=value)
        index += 1

    # Add a basic test case if no required attributes
    if not attrs["required"]:
        description = f"basic test for {role}"
        attributes = 'tabindex="0"'
        tests += test_case_template.format(role=role, index=index, description=description, attributes=attributes, attr_value="")

    cycling_logic = "\n".join(cycling_logic_parts)
    cycling_script = template.format(role=role, tests=tests, cycling_logic=cycling_logic)
    file_path = os.path.join(output_dir, f"{role}.html")
    with open(file_path, "w") as file:
        file.write(cycling_script)

print(f"Test files created in '{output_dir}' directory.")
