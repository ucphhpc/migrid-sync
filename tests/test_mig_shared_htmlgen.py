from collections import defaultdict

import html5lib

from mig.shared import htmlgen
from tests.support import FakeConfiguration, MigTestCase

# html namespace as default
ns = {"": "http://www.w3.org/1999/xhtml"}


class TestGetXgiHtmlHeader(MigTestCase):
    def test_user_menu_setup_disabled_if_setup_app_not_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=FakeConfiguration(user_interface=["V3"]),
            title="title",
            header="header",
            script_map=defaultdict(str),
        )

        parsed = html5lib.parse(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]', ns)
        link_setup = next(
            l for l in links if "link-setup" in l.attrib["class"].split()
        )

        assert "disable-link" in link_setup.attrib["class"].split()

    def test_user_menu_setup_enabled_if_setup_app_specified(self):
        result = htmlgen.get_xgi_html_header(
            configuration=FakeConfiguration(user_interface=["V3"]),
            title="title",
            header="header",
            script_map=defaultdict(str),
            base_menu=["setup"],
        )

        parsed = html5lib.parse(result)
        links = parsed.findall('.//div[@id="userMenu"]//a[@class]', ns)
        link_setup = next(
            l for l in links if "link-setup" in l.attrib["class"].split()
        )

        assert "disable-link" not in link_setup.attrib["class"].split()
