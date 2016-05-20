import unittest


class TestPluginIntegration(unittest.TestCase):

    """Test case for PalabosEngine class."""

    def test_plugin_integration(self):
        """Test to run Palabos modeling engine."""
        # Assert that we can import the Palabos plugin
        from simphony.engine import palabos_fileio_isothermal as lb

        # Check that the expected top level objects are available
        self.assertTrue(hasattr(lb, 'PalabosEngine'))


if __name__ == '__main__':
    unittest.main()
