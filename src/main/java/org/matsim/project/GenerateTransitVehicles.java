package org.matsim.project;

import org.matsim.api.core.v01.Id;
import org.matsim.api.core.v01.Scenario;
import org.matsim.core.config.Config;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.scenario.ScenarioUtils;
import org.matsim.vehicles.MatsimVehicleWriter;
import org.matsim.vehicles.Vehicle;
import org.matsim.vehicles.VehicleType;
import org.matsim.vehicles.VehicleUtils;
import org.matsim.vehicles.Vehicles;

import java.nio.file.Path;

public class GenerateTransitVehicles {
    public static void main(String[] args) {
        String vehiclesFile = "data/processed/transitVehicles.xml";

        Config config = ConfigUtils.createConfig();
        Scenario scenario = ScenarioUtils.createScenario(config);

        Vehicles vehicles = scenario.getVehicles();

        // Create VehicleType for bus
        VehicleType busType = VehicleUtils.createVehicleType(Id.create("bus", VehicleType.class));
        busType.getCapacity().setSeats(40);
        busType.getCapacity().setStandingRoom(20);
        busType.setMaximumVelocity(15.0); // m/s ≈ 54 km/h
        busType.setPcuEquivalents(2.5);

        // 🔑 Important: set network mode for non-car vehicles
        busType.setNetworkMode("bus");

        vehicles.addVehicleType(busType);

        // Add one bus
        Vehicle bus = VehicleUtils.createVehicle(Id.create("bus_1", Vehicle.class), busType);
        vehicles.addVehicle(bus);

        // Write output file
        Path vehiclesOut = Path.of(vehiclesFile);
        new MatsimVehicleWriter(vehicles).writeFile(vehiclesOut.toString());

        System.out.println("✅ Transit vehicles written to: " + vehiclesOut);
    }
}
