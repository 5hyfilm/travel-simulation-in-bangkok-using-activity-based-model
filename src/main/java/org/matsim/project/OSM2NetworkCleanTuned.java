package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.contrib.osm.networkReader.SupersonicOsmNetworkReader;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.algorithms.NetworkCleaner;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;

import java.nio.file.Paths;

public class OSM2NetworkCleanTuned {
    public static void main(String[] args) {
        // 🔹 Input / Output
        String inputFile = "data/raw/chula.osm.pbf";
        String rawNetworkFile = "data/processed/network_raw.xml";
        String cleanNetworkFile = "data/processed/network_clean.xml";
        String tunedNetworkFile = "data/processed/network_clean_tuned.xml";

        // 1. อ่าน OSM → สร้าง network
        SupersonicOsmNetworkReader reader = new SupersonicOsmNetworkReader.Builder()
                .setCoordinateTransformation(
                        TransformationFactory.getCoordinateTransformation(
                                TransformationFactory.WGS84, "EPSG:32647" // UTM zone 47N
                        )
                )
                .build();

        Network network = reader.read(Paths.get(inputFile));
        NetworkUtils.writeNetwork(network, rawNetworkFile);
        System.out.println("✅ เขียน network ดิบ: " + rawNetworkFile);

        // 2. Clean network
        Config config = ConfigUtils.createConfig();
        config.network().setInputFile(rawNetworkFile);
        Scenario scenario = ScenarioUtils.loadScenario(config);
        Network net = scenario.getNetwork();

        System.out.println("ก่อน clean: "
                + net.getNodes().size() + " nodes, "
                + net.getLinks().size() + " links");

        new NetworkCleaner().run(net);

        System.out.println("หลัง clean: "
                + net.getNodes().size() + " nodes, "
                + net.getLinks().size() + " links");

        NetworkUtils.writeNetwork(net, cleanNetworkFile);
        System.out.println("✅ เขียน network ที่ clean แล้ว: " + cleanNetworkFile);

        // 3. Tune parameters ตามประเภทถนน
        for (Link link : net.getLinks().values()) {
            String highway = (String) link.getAttributes().getAttribute("highway");
            if (highway == null) continue;

            switch (highway) {
                case "motorway":
                    link.setFreespeed(120.0 / 3.6); // 120 km/h
                    link.setCapacity(2000);
                    link.setNumberOfLanes(3);
                    break;
                case "trunk":
                    link.setFreespeed(80.0 / 3.6); // 80 km/h
                    link.setCapacity(1800);
                    link.setNumberOfLanes(2);
                    break;
                case "primary":
                    link.setFreespeed(60.0 / 3.6); // 60 km/h
                    link.setCapacity(1500);
                    link.setNumberOfLanes(2);
                    break;
                case "secondary":
                    link.setFreespeed(50.0 / 3.6);
                    link.setCapacity(1200);
                    link.setNumberOfLanes(1);
                    break;
                case "unclassified":
                case "residential":
                    link.setFreespeed(40.0 / 3.6);
                    link.setCapacity(1000);
                    link.setNumberOfLanes(1);
                    break;
                case "service":
                    link.setFreespeed(20.0 / 3.6);
                    link.setCapacity(600);
                    link.setNumberOfLanes(1);
                    break;
                default:
                    // keep MATSim defaults
                    break;
            }
        }

        // 4. เขียน network tuned
        NetworkUtils.writeNetwork(net, tunedNetworkFile);
        System.out.println("✅ เขียน network ที่ clean + tuned แล้ว: " + tunedNetworkFile);
    }
}
