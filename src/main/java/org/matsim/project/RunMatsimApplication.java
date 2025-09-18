/* *********************************************************************** *
 * project: org.matsim.*												   *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 * copyright       : (C) 2008 by the members listed in the COPYING,        *
 *                   LICENSE and WARRANTY file.                            *
 * email           : info at matsim dot org                                *
 *                                                                         *
 * *********************************************************************** *
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *   See also COPYING, LICENSE and WARRANTY file                           *
 *                                                                         *
 * *********************************************************************** */
package org.matsim.project;

import org.apache.logging.log4j.core.tools.picocli.CommandLine;
import org.matsim.api.core.v01.Scenario;
import org.matsim.application.MATSimApplication;
import org.matsim.core.config.Config;
import org.matsim.core.controler.Controler;
import org.matsim.core.controler.OutputDirectoryHierarchy.OverwriteFileSetting;
import org.matsim.contrib.otfvis.OTFVisLiveModule;
import org.matsim.vis.otfvis.OTFVisConfigGroup;
import org.matsim.core.config.ConfigUtils;


/**
 * @author nagel
 *
 */
@CommandLine.Command( header = ":: MyScenario ::", version = "1.0")
public class RunMatsimApplication extends MATSimApplication {

	public RunMatsimApplication() {
		super("scenarios/equil/config.xml");
	}

	public static void main(String[] args) {
		MATSimApplication.run(RunMatsimApplication.class, args);
	}

	@Override
	protected Config prepareConfig(Config config) {

		config.controller().setOverwriteFileSetting( OverwriteFileSetting.deleteDirectoryIfExists );

        OTFVisConfigGroup otf = ConfigUtils.addOrGetModule(config, OTFVisConfigGroup.class);

         //otf.setDrawLinkWidth(false);      // draw thin center lines
         otf.setLinkWidth(0.1f);           // or keep width but thinner

		return config;
	}

	@Override
	protected void prepareScenario(Scenario scenario) {

        scenario.getNetwork().getLinks().values().forEach(l -> {
            double dx = l.getToNode().getCoord().getX() - l.getFromNode().getCoord().getX();
            double dy = l.getToNode().getCoord().getY() - l.getFromNode().getCoord().getY();
            double straight = Math.hypot(dx, dy);

            // Enforce a reasonable minimum to avoid near-zero links
            double minLen = 15.0; // try 15–25 m for urban meshes
            double newLen = Math.max(straight, minLen);

            l.setLength(newLen);
        });

        // 2) Scale down freespeeds (m/s). Start with 0.3–0.5; calibrate later.
        double speedFactor = 0.5;  // try 0.3 if still too fast
        scenario.getNetwork().getLinks().values().forEach(l ->
                l.setFreespeed(l.getFreespeed() * speedFactor)
        );

        // 3) (optional) Also reduce capacity to create congestion delays
        // scenario.getNetwork().getLinks().values().forEach(l ->
        //     l.setCapacity(l.getCapacity() * 0.7)
        // );

	}

	@Override
	protected void prepareControler(Controler controler) {

		controler.addOverridingModule( new OTFVisLiveModule() ) ;
//		controler.addOverridingModule( new SimWrapperModule() ) ;

	}
}
