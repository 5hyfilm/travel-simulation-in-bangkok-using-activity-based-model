package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.io.OsmNetworkReader;
import org.matsim.core.network.NetworkUtils;

public class ConvertOSM {
    public static void main(String[] args) {
        // 1) Create an empty scenario & network container
        Scenario scenario = ScenarioUtils.createScenario(ConfigUtils.createConfig());
        Network network = scenario.getNetwork();

        // 2) Coordinate transform: keep WGS84 for now (safe & simple)
        //    You can switch to a projected CRS later.
        CoordinateTransformation ct =
                TransformationFactory.getCoordinateTransformation(
                        TransformationFactory.WGS84,  // from OSM (WGS84)
                        TransformationFactory.WGS84   // to (identity)
                );

        // 3) Read OSM and write MATSim network
        String in = "data/raw/pathumwan_M.osm";
        String out = "data/processed/network.xml.gz";
        OsmNetworkReader onr = new OsmNetworkReader(network, ct);
        onr.parse(in);

        NetworkUtils.writeNetwork(network, out);
        System.out.println("Wrote " + out);
    }
}
