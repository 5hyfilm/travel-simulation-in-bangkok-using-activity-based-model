package org.matsim.project;

import org.matsim.run.NetworkCleaner;

public class RunNetworkCleaner {
    public static void main(String[] args) {
        new NetworkCleaner().run(
                "data/processed/network.xml.gz",
                "data/processed/network.cleaned.xml.gz"
        );
        System.out.println("Wrote data/processed/network.cleaned.xml.gz");
    }
}