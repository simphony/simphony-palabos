from simphony.engine import ABCEngineExtension
from simphony.engine import EngineInterface
from simphony.engine.decorators import register

from simpalabos.fileio.isothermal.palabos_engine import \
    PalabosEngine
from .cuba_extension import CUBAExtension

__all__ = ["FileIOWrapper", "CUBAExtension"]


@register
class PalabosExtension(ABCEngineExtension):
    """Palabos extension.

    This extension provides support for Palabos engine.
    """

    def get_supported_engines(self):
        """Get metadata about supported engines.

        Returns
        -------
        list: a list of EngineMetadata objects
        """
        # TODO: Add proper features as soon as the metadata classes are ready.
        # Flow type, relaxation model etc.
        # palabos_features =\
        #     self.create_engine_metadata_feature(LAMINAR_FLOW, TRT)

        palabos_features = None

        palabos = self.create_engine_metadata('PALABOS',
                                              palabos_features,
                                              EngineInterface.FileIO)
        return [palabos]

    def create_wrapper(self, cuds, engine_name, engine_interface):
        """Creates a wrapper to the requested engine.

        Parameters
        ----------
        cuds: CUDS
          CUDS computational model data
        engine_name: str
          name of the engine, must be supported by this extension
        engine_interface: EngineInterface
          the interface to interact with engine

        Returns
        -------
        ABCEngineExtension: A wrapper configured with cuds and ready to run
        """
        if engine_interface == EngineInterface.Internal:
            raise Exception('Only FileIO interface is supported.')

        if engine_name == 'PALABOS':
            return FileIOWrapper(cuds=cuds)
        else:
            raise Exception('Only PALABOS engine is supported. '
                            'Unsupported engine: %s', engine_name)
