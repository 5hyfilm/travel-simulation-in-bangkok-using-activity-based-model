package org.matsim.project;

import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.network.io.NetworkWriter;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.api.core.v01.Scenario;
import org.matsim.core.utils.geometry.transformations.*;
import org.matsim.core.utils.geometry.CoordinateTransformation;


public class  ReprojectNetwork {
    public static void main(String[] args) {
        Scenario scenario = ScenarioUtils.createScenario(ConfigUtils.createConfig());

        // 1) Read your WGS84 network (degrees)
        new MatsimNetworkReader(scenario.getNetwork())
                .readFile("data/processed/network.cleaned.xml.gz");

        // 2) Transform coordinates WGS84 -> UTM zone 47N (Bangkok area)
        CoordinateTransformation ct =
                TransformationFactory.getCoordinateTransformation(
                        TransformationFactory.WGS84, "EPSG:32647");

        org.matsim.core.network.algorithms.NetworkTransform nt =
                new org.matsim.core.network.algorithms.NetworkTransform(ct);
        nt.run(scenario.getNetwork());

        // 3) Write new projected network
        new NetworkWriter(scenario.getNetwork())
                .write("data/processed/network_utm47.xml.gz");
    }
}
