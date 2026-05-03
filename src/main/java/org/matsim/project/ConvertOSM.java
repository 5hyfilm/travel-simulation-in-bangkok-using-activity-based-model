package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.algorithms.NetworkCleaner;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;
import org.matsim.core.utils.io.OsmNetworkReader;
import org.matsim.core.network.NetworkUtils;

public class ConvertOSM {
    public static void main(String[] args) {

        Scenario scenario = ScenarioUtils.createScenario(ConfigUtils.createConfig());
        Network network = scenario.getNetwork();

        CoordinateTransformation ct =
                TransformationFactory.getCoordinateTransformation(
                        TransformationFactory.WGS84,
                        "EPSG:32647"
                );

        String in  = "pipeline/output/network.osm";
        String out = "data/processed/network.xml.gz";

        OsmNetworkReader onr = new OsmNetworkReader(network, ct);

        // === เฉพาะถนนที่รถยนต์วิ่งได้ ===
        // format: hierarchy, type, lanes, freespeed(m/s), freespeedFactor, capacity/lane/hr

        // เดิม 36.11 (130 km/h) → ใหม่ 19.44 (70 km/h)
        onr.setHighwayDefaults(1, "motorway",        3, 19.44, 1.0, 2200);
        onr.setHighwayDefaults(1, "motorway_link",   1, 13.89, 1.0, 2000);

        // trunk เดิม 33.33 → ใหม่ 16.67 (60 km/h)
        onr.setHighwayDefaults(2, "trunk",           3, 16.67, 1.0, 2000);
        onr.setHighwayDefaults(2, "trunk_link",      1, 11.11, 1.0, 1800);

        // Primary — 80 km/h (ตอนโล่งขับเร็วกว่า limit)
        onr.setHighwayDefaults(3, "primary",         3, 22.22, 1.0, 1800);
        onr.setHighwayDefaults(3, "primary_link",    1, 16.67, 1.0, 1500);

        // Secondary — 70 km/h
        onr.setHighwayDefaults(4, "secondary",       2, 19.44, 1.0, 1500);
        onr.setHighwayDefaults(4, "secondary_link",  1, 16.67, 1.0, 1200);

        // Tertiary — 60 km/h
        onr.setHighwayDefaults(5, "tertiary",        2, 16.67, 1.0, 1200);
        onr.setHighwayDefaults(5, "tertiary_link",   1, 13.89, 1.0,  900);

        // Residential — 40 km/h (ซอยตอนว่าง)
        onr.setHighwayDefaults(6, "residential",     1, 11.11, 1.0,  600);
        onr.setHighwayDefaults(6, "unclassified",    1, 11.11, 1.0,  600);
        onr.setHighwayDefaults(6, "living_street",   1,  5.56, 1.0,  300);

        // Service — 25 km/h
        onr.setHighwayDefaults(7, "service",         1,  6.94, 1.0,  200);

        // === ไม่รวม (ไม่ต้อง setHighwayDefaults) ===
        // footway, path, steps, cycleway, pedestrian,
        // construction, proposed, busway, corridor,
        // platform, raceway, bridleway, elevator, 10100

        onr.parse(in);

        System.out.println("Cleaning network...");
        new NetworkCleaner().run(network);

        NetworkUtils.writeNetwork(network, out);
        System.out.println("Wrote " + out);
    }
}