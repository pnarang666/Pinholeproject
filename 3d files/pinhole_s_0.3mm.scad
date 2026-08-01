//==============================
// Parametric Single Pinhole Disc
// For SLA Printing
// Units: mm
//==============================

// PARAMETERS
disc_diameter = 25;      // Overall disc diameter
disc_thickness = 0.50;   // Disc thickness
hole_diameter = 2.00;    // Central pinhole

$fn = 200;               // Smooth circles

difference() {

    // Disc
    cylinder(
        d = disc_diameter,
        h = disc_thickness,
        center = false
    );

    // Pinhole
    translate([0,0,-1])
        cylinder(
            d = hole_diameter,
            h = disc_thickness + 2
        );

}