package org.matsim.project;

import org.matsim.api.core.v01.Coord;
import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.TransportMode;
import org.matsim.api.core.v01.population.*;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.population.io.PopulationWriter;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.core.utils.io.IOUtils;
import org.matsim.facilities.ActivityFacilities;
import org.matsim.facilities.ActivityFacility;
import org.matsim.facilities.MatsimFacilitiesReader;

import java.io.BufferedReader;
import java.util.*;

public class GeneratePlansFromActivitySim {

    public static void main(String[] args) throws Exception {

        String facilitiesFile = "data/processed/facilities.xml.gz";
        String tripsFile      = "data/raw/final_trips.csv";
        String outputPlans    = "data/processed/plans.xml.gz";

        Config config = ConfigUtils.createConfig();
        Scenario scenario = ScenarioUtils.createScenario(config);
        new MatsimFacilitiesReader(scenario).readFile(facilitiesFile);
        ActivityFacilities facilities = scenario.getActivityFacilities();

        Map<String, List<Id<ActivityFacility>>> zoneToFacilities = new HashMap<>();
        Random rand = new Random(42);
        List<Id<ActivityFacility>> allFacIds = new ArrayList<>(facilities.getFacilities().keySet());

        int maxZoneId = 100;
        for (Id<ActivityFacility> facId : allFacIds) {
            String randomZone = String.valueOf(rand.nextInt(maxZoneId) + 1);
            zoneToFacilities.computeIfAbsent(randomZone, k -> new ArrayList<>()).add(facId);
        }

        Population population = scenario.getPopulation();
        PopulationFactory popFactory = population.getFactory();

        try (BufferedReader br = IOUtils.getBufferedReader(tripsFile)) {
            br.readLine(); // Skip header
            String line;
            while ((line = br.readLine()) != null) {
                String[] rows = line.split(",", -1);
                if (rows.length < 15) continue;

                // --- CLEAN DATA: ลบ " และช่องว่างออกเพื่อความชัวร์ ---
                String pId = rows[0].replace("\"", "").trim();
                String purpose = rows[7].replace("\"", "").trim();
                double departTime = Double.parseDouble(rows[9].replace("\"", "").trim());
                String modeInput = rows[10].replace("\"", "").trim().toLowerCase();
                String destZone = rows[14].replace("\"", "").trim();

                // Mapping Mode
                String mode = TransportMode.car;
                if (modeInput.contains("walk")) mode = TransportMode.walk;
                else if (modeInput.contains("bike")) mode = TransportMode.bike;
                else if (modeInput.contains("pt") || modeInput.contains("loc")) mode = TransportMode.pt;

                Id<Person> personId = Id.createPersonId(pId);
                Person person = population.getPersons().get(personId);
                Plan plan;

                if (person == null) {
                    person = popFactory.createPerson(personId);
                    plan = popFactory.createPlan();
                    person.addPlan(plan);
                    population.addPerson(person);
                } else {
                    plan = person.getSelectedPlan();
                }

                if (plan.getPlanElements().size() > 0) {
                    plan.addLeg(popFactory.createLeg(mode));
                }

                Id<ActivityFacility> selectedFacId;
                if (zoneToFacilities.containsKey(destZone) && !zoneToFacilities.get(destZone).isEmpty()) {
                    selectedFacId = zoneToFacilities.get(destZone).get(rand.nextInt(zoneToFacilities.get(destZone).size()));
                } else {
                    selectedFacId = allFacIds.get(rand.nextInt(allFacIds.size()));
                }

                Coord coord = facilities.getFacilities().get(selectedFacId).getCoord();
                Activity act = popFactory.createActivityFromCoord(purpose, coord);
                act.setFacilityId(selectedFacId);
                act.setEndTime(departTime * 3600.0);
                plan.addActivity(act);
            }
        }

        new PopulationWriter(population).write(outputPlans);
        System.out.println("Generated plans without quotes for " + population.getPersons().size() + " agents.");
    }
}