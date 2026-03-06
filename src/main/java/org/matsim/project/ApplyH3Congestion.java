package org.matsim.project;

import com.uber.h3core.H3Core;
import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.network.io.NetworkWriter;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.geometry.CoordinateTransformation;
import org.matsim.core.utils.geometry.transformations.TransformationFactory;

import java.io.BufferedReader;
import java.io.FileReader;
import java.util.HashMap;
import java.util.Map;

/**
 * Reads a CSV of H3 cells (resolution 8) with speed factors,
 * finds all network links whose midpoint falls in each congested cell,
 * and scales their freespeed accordingly.
 *
 * Input CSV format (no header required to change):
 *   h3_index,speed_factor
 *   8a3968c7a5fffff,0.3
 *   8a3968c7a4fffff,0.6
 *
 * Run after RecalcSpeedsBangkok so that freespeeds are already set correctly.
 */
public class ApplyH3Congestion {

    static final String NETWORK_IN   = "data/processed/network_utm47.speeds_lanes_cap.xml.gz";
    static final String CONGESTION_CSV = "data/raw/h3_congestion.csv";
    static final String NETWORK_OUT  = "data/processed/network_congested.xml.gz";
    static final int    H3_RESOLUTION = 8;

    public static void main(String[] args) throws Exception {

        // Allow overriding paths via args: [networkIn, congestionCsv, networkOut]
        String networkIn    = args.length > 0 ? args[0] : NETWORK_IN;
        String congestionCsv = args.length > 1 ? args[1] : CONGESTION_CSV;
        String networkOut   = args.length > 2 ? args[2] : NETWORK_OUT;

        // 1. Load congestion map: h3_index → speed_factor
        Map<String, Double> h3ToFactor = loadCongestionCsv(congestionCsv);
        System.out.println("Loaded " + h3ToFactor.size() + " congested H3 cells.");

        // 2. Load network (coordinates in UTM47 / EPSG:32647)
        Scenario scenario = ScenarioUtils.createScenario(ConfigUtils.createConfig());
        new MatsimNetworkReader(scenario.getNetwork()).readFile(networkIn);
        Network network = scenario.getNetwork();
        System.out.println("Loaded network with " + network.getLinks().size() + " links.");

        // 3. Coordinate transformer: UTM47 → WGS84
        CoordinateTransformation toWgs84 = TransformationFactory.getCoordinateTransformation(
                "EPSG:32647", TransformationFactory.WGS84);

        // 4. H3 core instance
        H3Core h3 = H3Core.newInstance();

        // 5. Iterate links: midpoint → WGS84 → H3 cell → apply factor
        int modified = 0;
        for (Link link : network.getLinks().values()) {
            Coord from = link.getFromNode().getCoord();
            Coord to   = link.getToNode().getCoord();

            double midX = (from.getX() + to.getX()) / 2.0;
            double midY = (from.getY() + to.getY()) / 2.0;

            Coord midWgs84 = toWgs84.transform(new Coord(midX, midY));
            double lat = midWgs84.getY();
            double lon = midWgs84.getX();

            String cell = h3.latLngToCellAddress(lat, lon, H3_RESOLUTION);

            if (h3ToFactor.containsKey(cell)) {
                double factor = h3ToFactor.get(cell);
                link.setFreespeed(link.getFreespeed() * factor);
                modified++;
            }
        }

        System.out.println("Applied congestion to " + modified + " links.");

        // 6. Write modified network
        new NetworkWriter(network).write(networkOut);
        System.out.println("Wrote: " + networkOut);
    }

    private static Map<String, Double> loadCongestionCsv(String path) throws Exception {
        Map<String, Double> map = new HashMap<>();
        try (BufferedReader br = new BufferedReader(new FileReader(path))) {
            br.readLine(); // skip header: h3_index,speed_factor
            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank()) continue;
                String[] parts = line.split(",", 2);
                String h3Index = parts[0].trim();
                double factor  = Double.parseDouble(parts[1].trim());
                map.put(h3Index, factor);
            }
        }
        return map;
    }
}
