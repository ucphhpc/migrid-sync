from __future__ import print_function

from tests.support import MigTestCase, testmain

from mig.shared.templates import TemplateStore, cache_dir, template_dirs


class TestMigSharedTemplates(MigTestCase):
    def _provide_configuration(self):
        return 'testconfig'

    def test_the_creation_of_a_template_store(self):
        store = TemplateStore.populated(template_dirs(), cache_dir=cache_dir())
        self.assertIsInstance(store, TemplateStore)

    def test_a_listing_all_templates(self):
        store = TemplateStore.populated(template_dirs(), cache_dir=cache_dir())
        self.assertEqual(len(store.list_templates()), 2)

    def test_grab_template(self):
        store = TemplateStore.populated(template_dirs(), cache_dir=cache_dir())
        template = store.grab_template('other', 'partial', 'html')
        pass

    def test_variables_for_remplate_ref(self):
        store = TemplateStore.populated(template_dirs(), cache_dir=cache_dir())
        template_vars = store.extract_variables('partial_something.html.jinja')
        self.assertEqual(template_vars, set(['content']))


if __name__ == '__main__':
    testmain()
