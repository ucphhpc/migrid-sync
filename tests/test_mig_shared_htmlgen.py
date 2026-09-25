from collections import defaultdict

from lxml import etree

from mig.shared import htmlgen
from tests.support import MigTestCase


class TestGetXgiHtmlHeader(MigTestCase):

    def _provide_configuration(self) -> str:
        return "testconfig"

    def test_user_menu_setup_disabled_if_setup_app_not_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
        )

        parsed = etree.HTML(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]')
        link_setup = next(
            l for l in links if "link-setup" in l.attrib["class"].split()
        )

        assert "disable-link" in link_setup.attrib["class"].split()

    def test_user_menu_setup_enabled_if_setup_app_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=self.configuration,
            title="title",
            header="header",
            script_map=defaultdict(str),
            base_menu=["setup"],
        )

        parsed = etree.HTML(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]')
        link_setup = next(
            l for l in links if "link-setup" in l.attrib["class"].split()
        )

        assert "disable-link" not in link_setup.attrib["class"].split()
