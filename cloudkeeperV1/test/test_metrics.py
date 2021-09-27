from cloudkeeperv1.metrics import GraphCollector
from cklib.graph import GraphContainer
from prometheus_client.core import GaugeMetricFamily


def test_metrics():
    gc = GraphContainer(cache_graph=False)
    c = GraphCollector(gc)
    for metric in c.collect():
        assert type(metric) == GaugeMetricFamily
