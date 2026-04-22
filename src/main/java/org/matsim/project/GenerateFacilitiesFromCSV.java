package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.NetworkUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.facilities.*;

import org.matsim.core.utils.io.IOUtils;

import java.io.BufferedReader;
import java.nio.file.Paths;

public class GenerateFacilitiesFromCSV {

    public static void main(String[] args) throws Exception {

        String networkFile = "data/processed/network_utm47.xml.gz";
        String csvFile     = "data/raw/facilities_cleaned.csv";
        String outFile     = "data/processed/facilities.xml.gz";

        // 1) Load network
        Config config = ConfigUtils.createConfig();
        var scenario = ScenarioUtils.createScenario(config);
        Network network = scenario.getNetwork();
        new MatsimNetworkReader(network).readFile(networkFile);

        // 2) Facilities container
        ActivityFacilities facilities = scenario.getActivityFacilities();
        ActivityFacilitiesFactory factory = facilities.getFactory();

        int created = 0;
        int skipped = 0;

        // 3) Read CSV (9 columns)
        try (BufferedReader br = IOUtils.getBufferedReader(csvFile)) {
            String header = br.readLine();   // ข้าม header
            String line;

            while ((line = br.readLine()) != null) {
                if (line.trim().isEmpty()) continue;

                String[] parts = line.split(",", -1);
                if (parts.length < 5) {          // ต้องมีอย่างน้อย 5 คอลัมน์
                    skipped++;
                    continue;
                }

                try {
                    // คอลัมน์จริงจากไฟล์ของคุณ:
                    // 0: osmid, 1: name, 2: activity_type, 3: x, 4: y, ...
                    String osmid = parts[0].trim();
                    String activityType = parts[2].trim();   // ← สำคัญ: activity_type อยู่ index 2
                    double x = Double.parseDouble(parts[3].trim());
                    double y = Double.parseDouble(parts[4].trim());

                    Coord coord = new Coord(x, y);

                    // หา nearest link
                    Link nearestLink = NetworkUtils.getNearestLink(network, coord);

                    // สร้าง Facility
                    Id<ActivityFacility> facId = Id.create("fac_" + osmid, ActivityFacility.class);
                    ActivityFacility facility = factory.createActivityFacility(facId, coord, nearestLink.getId());

                    // เพิ่ม activity type
                    ActivityOption option = factory.createActivityOption(activityType);
                    facility.addActivityOption(option);

                    facilities.addActivityFacility(facility);
                    created++;

                } catch (Exception e) {
                    skipped++;
                    // System.out.println("Error on line: " + line.substring(0, Math.min(100, line.length())));
                }
            }
        }

        // 4) Write output
        new FacilitiesWriter(facilities).write(outFile);

        System.out.println("✅ Facilities generation completed!");
        System.out.println("Created facilities : " + created);
        System.out.println("Skipped lines      : " + skipped);
        System.out.println("Output file        : " + Paths.get(outFile).toAbsolutePath());
    }
}