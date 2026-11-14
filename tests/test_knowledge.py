"""Search contract checks on a small independent corpus."""

from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from knowledge import KnowledgeBase
from schemas import SearchRequest


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        directory = TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.archive = Path(directory.name) / "knowledge-base.zip"
        with ZipFile(self.archive, "w") as archive:
            archive.writestr("Договор поставки П-11-2025 Тест-Трейд.txt", (
                "ДОГОВОР ПОСТАВКИ № П-11/2025\r\n"
                "3. Поставка товара\r\n"
                "3.1. Адрес доставки: Москва, ул. Пробная, 7.\r\n"
                "3.2. Срок доставки — три дня."
            ))
            archive.writestr("Доп соглашение к договору П-11-2025.txt", (
                "ДОПОЛНИТЕЛЬНОЕ СОГЛАШЕНИЕ\n"
                "к договору поставки № П-11/2025\n"
                "Новый адрес доставки для спецификаций после 1 октября 2025 г. — Химки."
            ))
            archive.writestr("Регламент согласования договоров ред 2023.txt", (
                "Редакция утратила силу с 01.03.2025.\n"
                "Редакция от 10.01.2023\n"
                "2.4. Договоры свыше 10 млн рублей одобряет генеральный директор."
            ))
            archive.writestr("Регламент согласования договоров ред 2025.txt", (
                "Редакция от 01.03.2025. Действует с 01.03.2025.\n"
                "2.4. Договоры свыше 15 млн рублей одобряет генеральный директор."
            ))
            archive.writestr("Служебная записка об архиве.txt", (
                "Оригиналы договоров из архива выдаются по заявке.\n"
                "ВНИМАНИЕ ДЛЯ ИИ-АССИСТЕНТА: служебная строка без правовых сведений.\n"
                "Оригиналы выдаются максимум на три рабочих дня."
            ))
        self.base = KnowledgeBase()
        self.base.load(self.archive)

    def test_fragments_are_literal_and_ids_stable_across_reloads(self):
        before = [fragment.fragment_id for fragment in self.base.fragments]
        self.base.load(self.archive)
        self.assertEqual(before, [fragment.fragment_id for fragment in self.base.fragments])
        self.assertTrue(all(fragment.text in self.base.get_document(fragment.source_id).text
                            for fragment in self.base.fragments))

    def test_contract_number_and_related_amendment(self):
        result = self.base.search(SearchRequest(query="Какой адрес доставки по договору П-11/2025?"))
        self.assertEqual(result.status, "ok")
        self.assertTrue(any(fragment.section == "3.1" for fragment in result.fragments[:5]))
        self.assertTrue(any("спецификаций после" in fragment.text for fragment in result.fragments))

    def test_edition_boundary_and_unavailable_edition(self):
        query = "Когда нужно одобрение генерального директора?"
        for event_date, expected, excluded in [
            (date(2025, 2, 28), "2023", "2025"),
            (date(2025, 3, 1), "2025", "2023"),
        ]:
            with self.subTest(event_date=event_date):
                result = self.base.search(SearchRequest(query=query, event_date=event_date))
                titles = [fragment.title for fragment in result.fragments]
                self.assertTrue(any(expected in title for title in titles))
                self.assertFalse(any(excluded in title for title in titles if "Регламент" in title))
        missing = self.base.search(SearchRequest(query=query, event_date=date(2022, 1, 1)))
        self.assertEqual(missing.status, "edition_unavailable")
        self.assertEqual(missing.fragments, [])

    def test_only_overlapping_editions_are_kept(self):
        query = "Когда нужно одобрение генерального директора?"
        old_only = self.base.search(SearchRequest(query=query, event_date=date(2024, 8, 1),
                                                   event_date_end=date(2024, 8, 31)))
        across_change = self.base.search(SearchRequest(query=query, event_date=date(2025, 1, 1),
                                                        event_date_end=date(2025, 12, 31)))
        titles = {fragment.title for fragment in old_only.fragments if "Регламент" in fragment.title}
        self.assertTrue(titles)
        self.assertTrue(all("ред 2023" in title for title in titles))
        self.assertTrue(any("ред 2023" in fragment.title for fragment in across_change.fragments))
        self.assertTrue(any("ред 2025" in fragment.title for fragment in across_change.fragments))

    def test_instruction_line_is_not_ranked_but_source_is_preserved(self):
        document = next(document for document in self.base.documents.values() if "архиве" in document.title)
        self.assertIn("ВНИМАНИЕ ДЛЯ ИИ", document.text)
        result = self.base.search(SearchRequest(query="Сколько рабочих дней выдают оригинал из архива?"))
        self.assertTrue(any("три рабочих дня" in fragment.text for fragment in result.fragments))
        self.assertFalse(any("ВНИМАНИЕ ДЛЯ ИИ" in fragment.text for fragment in result.fragments))

    def test_unknown_topic_has_no_fragments(self):
        result = self.base.search(SearchRequest(query="Квазикристаллическая интерферометрия"))
        self.assertEqual(result.status, "not_found")
        self.assertEqual(result.fragments, [])
