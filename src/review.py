import re

import automatic_code_review_commons as commons


def check_order_changed(lines_changed, lines_source):
    lines_import_changed = []
    lines_import_source = []

    for line in lines_source:
        line = line.strip()

        if line.startswith("import "):
            lines_import_source.append(line)

    for line in lines_changed:
        line = line.strip()

        if line.startswith("import "):
            lines_import_changed.append(line)

    return lines_import_source != lines_import_changed


def adjust_order(lines_with_import, regex_order):
    lines_with_import_ordered = []
    remaining_imports = set(lines_with_import)

    for regex_object in regex_order:
        regex_type = regex_object["orderType"]
        regex_patterns = regex_object["regex"]

        import_by_group = []

        for pattern in regex_patterns:
            matched_imports = sorted([imp for imp in remaining_imports if re.match(pattern, imp)])
            import_by_group.extend(matched_imports)
            remaining_imports.difference_update(matched_imports)

        if import_by_group:
            if regex_type == "group":
                import_by_group.sort()

        lines_with_import_ordered.extend(import_by_group)

    if remaining_imports:
        lines_with_import_ordered.extend(sorted(remaining_imports))

    return lines_with_import_ordered


def remove_duplicate_imports(imports):
    retorno = []

    for import_ in imports:
        if import_ not in retorno:
            retorno.append(import_)

    return retorno


def verify(path, regex_order):
    print(f"Verificando arquivo {path}")

    with open(path, "r") as arquivo:
        lines = arquivo.readlines()

    lines_without_import = []
    lines_with_import = []

    for line in lines:

        if line.startswith("import "):
            lines_with_import.append(line)
        else:
            lines_without_import.append(line)

    lines_with_import = remove_duplicate_imports(lines_with_import)
    lines_with_import_ordered = adjust_order(lines_with_import, regex_order)

    linhas_fix = lines_with_import_ordered
    linhas_fix.extend(lines_without_import)

    if check_order_changed(linhas_fix, lines):
        print(f"MUDOU ALGUMA ORDEM: {path}")
        return True, lines_with_import_ordered, linhas_fix

    return False, lines_with_import_ordered, linhas_fix


def ordered_to_string(ordered):
    return (
        "<pre>"
        + "".join(
            [
                order.replace(">", "&gt;").replace("<", "&lt;").replace("\n", "<br>")
                for order in ordered[1:-1]
            ]
        )
        + "</pre>"
    )


def review(config):
    path_source = config["path_source"]
    comment_description_pattern = config["message"]

    merge = config["merge"]
    changes = merge["changes"]

    regex_order = config["regexOrder"]

    comments = []

    for change in changes:
        if change["deleted_file"]:
            continue

        new_path = change["new_path"]
        full_path = path_source + "/" + new_path

        if not full_path.endswith((".qml")):
            continue

        changed, ordered, _ = verify(path=full_path, regex_order=regex_order)

        if not changed:
            continue

        comment_path = new_path
        comment_description = f"{comment_description_pattern}"
        comment_description = comment_description.replace("${FILE_PATH}", comment_path)
        comment_description = comment_description.replace("${ORDERED}", ordered_to_string(ordered))

        comments.append(
            commons.comment_create(
                comment_id=commons.comment_generate_id(comment_description),
                comment_path=comment_path,
                comment_description=comment_description,
                comment_snipset=False,
                comment_end_line=1,
                comment_start_line=1,
                comment_language=None,
            )
        )

    return comments
