"""Conformidade — princípio VIII da constituição.

O núcleo do domínio não conhece fornecedor. Este teste é a diferença entre
esse princípio ser um parágrafo e ser uma restrição.
"""

import ast
import os
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORE = os.path.join(ROOT, "src", "core")

#: Nomes de fornecedor que não podem aparecer no núcleo, em nenhuma forma.
VENDOR_WORDS = ("clickbank", "clkbank", "digistore", "buygoods")


def core_files():
    for base, _, names in os.walk(CORE):
        for name in names:
            if name.endswith(".py"):
                yield os.path.join(base, name)


class CoreIsVendorFree(unittest.TestCase):
    def test_core_nao_importa_adapters(self):
        for path in core_files():
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read(), path)
            for node in ast.walk(tree):
                modules = []
                if isinstance(node, ast.Import):
                    modules = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    modules = [node.module]
                for module in modules:
                    self.assertFalse(
                        module.startswith("src.adapters"),
                        f"{os.path.relpath(path, ROOT)} importa {module}: "
                        f"a dependência aponta para o lado errado",
                    )

    def test_nenhum_nome_de_fornecedor_no_core(self):
        for path in core_files():
            with open(path, encoding="utf-8") as fh:
                content = fh.read().lower()
            for word in VENDOR_WORDS:
                self.assertNotIn(
                    word,
                    content,
                    f"{os.path.relpath(path, ROOT)} menciona {word!r}. "
                    f"Trocar de rede tem de ser escrever um adapter.",
                )

    def test_adapters_podem_importar_o_core(self):
        # A direção correta da dependência. Se este teste falhar, a
        # arquitetura foi invertida em algum lugar.
        from src.adapters.clickbank import events

        self.assertTrue(hasattr(events, "to_order"))


if __name__ == "__main__":
    unittest.main()
