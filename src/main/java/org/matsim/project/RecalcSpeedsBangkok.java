package org.matsim.project;

import org.matsim.api.core.v01.Scenario;
import org.matsim.api.core.v01.network.Link;
import org.matsim.api.core.v01.network.Network;
import org.matsim.core.config.ConfigUtils;
import org.matsim.core.network.io.MatsimNetworkReader;
import org.matsim.core.network.io.NetworkWriter;
import org.matsim.core.scenario.ScenarioUtils;

import java.util.HashMap;
import java.util.Map;


public class RecalcSpeedsBangkok {
    // km/h defaults by OSM highway=* (tune to your liking)
    static final Map<String, Double> HWY_KMH = new HashMap<>() {{
        put("motorway",       80.0);
        put("trunk",          55.0);
        put("primary",        50.0);
        put("secondary",      40.0);
        put("tertiary",       30.0);
        put("unclassified",   25.0);
        put("residential",    20.0);
        put("service",        15.0);
        put("living_street",  10.0);
    }};

    // default lanes by highway=* if OSM lanes not present
    static final Map<String, Double> HWY_LANES = new HashMap<>() {{
        put("motorway",      3.0);
        put("trunk",         2.5);
        put("primary",       2.0);
        put("secondary",     1.5);
        put("tertiary",      1.5);
        put("unclassified",  1.0);
        put("residential",   1.0);
        put("service",       1.0);
        put("living_street", 1.0);
    }};

    // capacity per lane (veh/h/lane). Adjust per your calibration.
    static final double CAP_PER_LANE = 1800.0;

    static double kmh2ms(double v) { return v / 3.6; }

    public static void main(String[] args) {
        String in  = "data/processed/network_utm47.xml.gz";
        String out = "data/processed/network_utm47.speeds_lanes_cap.xml.gz";

        Scenario sc = ScenarioUtils.createScenario(ConfigUtils.createConfig());
        new MatsimNetworkReader(sc.getNetwork()).readFile(in);
        Network net = sc.getNetwork();

        for (Link link : net.getLinks().values()) {

            // ---------- SPEED ----------
            Double fromMaxspeed = tryParseMaxspeed(link);
            if (fromMaxspeed != null) {
                link.setFreespeed(fromMaxspeed); // already m/s
            } else {
                String hwy = hwy(link);
                Double kmh = (hwy != null) ? HWY_KMH.get(hwy) : null;
                link.setFreespeed(kmh2ms(kmh != null ? kmh : 35.0));
            }

            // ---------- LANES ----------
            // Prefer explicit OSM lanes if present; else fallback by highway type
            double lanes = tryParseLanes(link);
            if (Double.isNaN(lanes) || lanes <= 0) {
                String hwy = hwy(link);
                lanes = (hwy != null && HWY_LANES.containsKey(hwy)) ? HWY_LANES.get(hwy) : 1.0;
            }
            link.setNumberOfLanes(lanes);

            // ---------- CAPACITY ----------
            // MATSim expects capacity per link (veh/h, per direction for one-way links).
            // Common rule: capacity ≈ CAP_PER_LANE * lanes
            double cap = CAP_PER_LANE * lanes;
            link.setCapacity(cap);
        }

        new NetworkWriter(net).write(out);
        System.out.println("Wrote " + out);
    }

    // --- helpers ---
    static String asString(Link l, String key) {
        Object v = l.getAttributes().getAttribute(key);
        return v == null ? null : String.valueOf(v);
    }

    static String hwy(Link l) {
        String[] keys = {
                "highway",
                "osm:way:highway",
                "type",        // <-- your file uses this
                "origType",    // <-- often present in core reader outputs
                "fclass"       // <-- some converters use this
        };
        for (String k : keys) {
            String v = asString(l, k);
            if (v != null && !v.isBlank()) return v;
        }
        return null;
    }

    // Parses common maxspeed forms: "50", "50 km/h", "30 mph"
    static Double tryParseMaxspeed(Link l) {
        String raw = asString(l, "maxspeed");
        if (raw == null) raw = asString(l, "osm:way:maxspeed");
        if (raw == null) return null;

        String s = raw.trim().toLowerCase();
        try {
            if (s.matches("^\\d+(\\.\\d+)?$")) return kmh2ms(Double.parseDouble(s)); // assume km/h
            if (s.contains("km")) {
                String n = s.replaceAll("[^0-9.]", "");
                return kmh2ms(Double.parseDouble(n));
            }
            if (s.contains("mph")) {
                String n = s.replaceAll("[^0-9.]", "");
                double mph = Double.parseDouble(n);
                return (mph * 1609.344) / 3600.0;
            }
        } catch (Exception ignore) { }
        return null;
    }

    // Read lanes from OSM attributes when available
    static double tryParseLanes(Link l) {
        // Prefer exact 'lanes' if present
        String raw = asString(l, "lanes");
        if (raw == null) raw = asString(l, "osm:way:lanes");
        // You might also see lanes:forward/backward on two-way ways before splitting, but after import links are directed.

        if (raw == null) return Double.NaN;
        try {
            // Some OSM have "2;1" etc. Keep the first number.
            String first = raw.split("[;|,]")[0].trim();
            return Double.parseDouble(first);
        } catch (Exception e) {
            return Double.NaN;
        }
    }
}
