import os
import shutil

from tests.support import MigTestCase, testmain, \
    MIG_BASE, TEST_DATA_DIR, TEST_OUTPUT_DIR

from mig.lib.templates import TemplateStore, template_dirs, \
    init_global_templates

TEST_CACHE_DIR = os.path.join(TEST_OUTPUT_DIR, '__template_cache__')
TEST_TMPL_DIR = os.path.join(TEST_DATA_DIR, 'templates')


class TestMigSharedTemplates_instance(MigTestCase):
    def after_each(self):
        shutil.rmtree(TEST_CACHE_DIR, ignore_errors=True)

    def _provide_configuration(self):
        return 'testconfig'

    def test_the_creation_of_a_template_store(self):
        store = TemplateStore.populated(TEST_TMPL_DIR, cache_dir=TEST_CACHE_DIR)
        self.assertIsInstance(store, TemplateStore)

    def test_a_listing_all_templates(self):
        store = TemplateStore.populated(TEST_TMPL_DIR, cache_dir=TEST_CACHE_DIR)
        self.assertEqual(len(store.list_templates()), 2)

    def test_grab_template(self):
        store = TemplateStore.populated(TEST_TMPL_DIR, cache_dir=TEST_CACHE_DIR)
        template = store.grab_template('other', 'test', 'html')
        pass

    def test_variables_for_remplate_ref(self):
        store = TemplateStore.populated(TEST_TMPL_DIR, cache_dir=TEST_CACHE_DIR)
        template_vars = store.extract_variables('test_something.html.jinja')
        self.assertEqual(template_vars, set(['content']))


class TestMigSharedTemplates_global(MigTestCase):
    def _provide_configuration(self):
        return 'testconfig'

    def test_cache_location(self):
        store = init_global_templates(self.configuration)

        relative_cache_dir = os.path.relpath(store.cache_dir, MIG_BASE)
        self.assertEqual(relative_cache_dir, 'mig/assets/templates/__jinja__')


if __name__ == '__main__':
    testmain()
