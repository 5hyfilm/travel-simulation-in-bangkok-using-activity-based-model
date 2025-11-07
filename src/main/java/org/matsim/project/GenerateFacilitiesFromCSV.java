package org.matsim.project;

import org.matsim.api.core.v01.*;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.facilities.*;
import org.matsim.core.utils.io.IOUtils;
import org.matsim.core.network.NetworkUtils;

import java.io.BufferedReader;
import java.nio.file.Paths;

public class GenerateFacilitiesFromCSV {
    public static void main(String[] args) throws Exception {
        // Adjust paths as needed
        String networkFile = "data/processed/network_utm47.xml.gz";
        String csvFile     = "data/raw/facilities.csv";
        String outFile     = "data/processed/facilities.xml.gz";

        // 1) Scenario + load network
        Config config = ConfigUtils.createConfig();
        var scenario = ScenarioUtils.createScenario(config);
        Network network = scenario.getNetwork();
        new MatsimNetworkReader(network).readFile(networkFile);

        // 2) Prepare facilities container
        ActivityFacilities facilities = scenario.getActivityFacilities();
        ActivityFacilitiesFactory fFactory = facilities.getFactory();

        // 3) Read CSV
        try (BufferedReader br = IOUtils.getBufferedReader(csvFile)) {
            String header = br.readLine(); // id,type,x,y
            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank()) continue;
                String[] parts = line.split(",", -1);
                String id = parts[0].trim();
                String type = parts[1].trim();
                double x = Double.parseDouble(parts[2].trim());
                double y = Double.parseDouble(parts[3].trim());

                Coord coord = new Coord(x, y);

                // 4) Find nearest link on the network for better routing
                Link nearest = NetworkUtils.getNearestLink(network, coord);

                // 5) Create facility
                ActivityFacility fac = fFactory.createActivityFacility(Id.create(id, ActivityFacility.class), coord, nearest.getId());
                // Add activity option
                ActivityOption opt = fFactory.createActivityOption(type);
                fac.addActivityOption(opt);

                facilities.addActivityFacility(fac);
            }
        }

        // 6) Write facilities.xml.gz
        new FacilitiesWriter(facilities).write(outFile);
        System.out.println("Wrote: " + Paths.get(outFile).toAbsolutePath());
    }
}
