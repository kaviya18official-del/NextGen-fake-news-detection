"""Script to generate a curated, realistic sample news dataset for NextGen NewsVerify.
Includes genuine news reports from Reuters/AP style reporting and debunked false/conspiracy narratives.
"""

import csv
import os

DATA = [
    # REAL NEWS EXAMPLES
    ("The Federal Reserve announced on Wednesday that it will hold benchmark interest rates steady in the range of 5.25% to 5.50% following its two-day policy meeting, citing sustained inflation progress.", "Real"),
    ("NASA's James Webb Space Telescope has captured unprecedented high-resolution infrared images of the Ring Nebula, revealing intricate filament structures within the expanding shell of ionized gas.", "Real"),
    ("The World Health Organization confirmed an increase in seasonal influenza cases across parts of the Northern Hemisphere, advising vulnerable populations to get vaccinated before winter peaks.", "Real"),
    ("The European Union Parliament voted to approve landmark comprehensive regulations governing artificial intelligence applications, establishing stringent risk tiers and transparency mandates for foundation models.", "Real"),
    ("The Department of Labor reported that the United States economy added 175,000 nonfarm payroll jobs last month, while the national unemployment rate held steady at 3.9 percent.", "Real"),
    ("Scientists at the European Organization for Nuclear Research (CERN) celebrated the 12th anniversary of confirming the discovery of the Higgs boson, continuing high-luminosity particle collision experiments.", "Real"),
    ("The International Energy Agency published its annual energy outlook report, forecasting that renewable energy capacity will double globally over the next five years driven by solar and wind adoption.", "Real"),
    ("The Supreme Court issued a 6-3 ruling regarding regulatory authority of federal administrative agencies, overturning the long-standing legal framework known as the Chevron deference doctrine.", "Real"),
    ("Pfizer and BioNTech announced favorable phase 3 clinical trial data for their combination vaccine targeting both influenza and COVID-19 in adult participants aged 18 to 64.", "Real"),
    ("Astronomers at the European Southern Observatory detected a dormant stellar-mass black hole with a mass 33 times that of the Sun located within the Milky Way constellation Aquila.", "Real"),
    ("The United Kingdom Office for National Statistics reported that the Consumer Prices Index inflation rate dropped to 2.0 percent, reaching the Bank of England's official target for the first time in three years.", "Real"),
    ("The Centers for Disease Control and Prevention issued updated guidelines for respiratory virus prevention, focusing on symptom-based recovery rather than mandatory five-day isolation periods.", "Real"),
    ("Japan's space agency JAXA successfully retrieved orbital data from its SLIM lunar lander after it achieved a pinpoint touchdown on the Moon's surface within 55 meters of the targeted landing zone.", "Real"),
    ("The Environmental Protection Agency unveiled strict new drinking water standards limiting six types of synthetic per- and polyfluoroalkyl substances (PFAS), also known as forever chemicals.", "Real"),
    ("The International Monetary Fund upgraded its global economic growth projection for the current fiscal year to 3.2 percent, citing resilient consumer spending in major advanced economies.", "Real"),
    ("A bipartisan group of US senators introduced comprehensive legislation aimed at establishing federal data privacy standards and restricting algorithmic targeting for children on social platforms.", "Real"),
    ("Geologists monitoring the Kilauea volcano in Hawaii reported a series of minor summit earthquakes and ground deformation indicative of magma movement within the Halemaʻumaʻu caldera.", "Real"),
    ("The United Nations Security Council adopted a resolution calling for an immediate humanitarian ceasefire in Gaza during the holy month of Ramadan, with fourteen member states voting in favor.", "Real"),
    ("The Food and Drug Administration granted accelerated approval for a new targeted immunotherapy drug designed to treat patients with advanced unresectable non-small cell lung cancer.", "Real"),
    ("Automotive industry analysts confirmed that electric vehicle deliveries worldwide reached a record 13.6 million units over the past calendar year, led by strong expansion in Asian markets.", "Real"),
    ("Archaeologists excavating near the ancient Roman city of Pompeii uncovered an elaborate banquet hall featuring remarkably preserved mythological frescoes depicting Helen of Troy.", "Real"),
    ("The National Oceanic and Atmospheric Administration stated that ocean sea surface temperatures set an all-time monthly record high for the fourteenth consecutive month.", "Real"),
    ("The Australian Bureau of Meteorology announced the end of the 2023-2024 El Niño climate event, noting that the tropical Pacific Ocean has returned to neutral atmospheric conditions.", "Real"),
    ("The Ministry of Health in Kenya launched a nationwide distribution campaign for the newly approved R21 malaria vaccine, aiming to protect over 300,000 infants in high-transmission counties.", "Real"),
    ("The Swiss National Bank surprised global financial markets by cutting its key policy rate by 25 basis points to 1.50 percent, pointing to effective control over domestic inflation.", "Real"),
    ("The Federal Aviation Administration ordered temporary ground inspections on certain Boeing 737 MAX 9 aircraft following an in-flight fuselage panel blowout on an Alaska Airlines flight.", "Real"),
    ("Researchers at MIT developed a novel desalinization membrane powered directly by solar energy that achieves a record-setting freshwater extraction rate without fouling from concentrated brine.", "Real"),
    ("The Swedish Royal Academy of Sciences announced the Nobel Prize in Physics, honoring three physicists for developing experimental methods that generate attosecond pulses of light.", "Real"),
    ("The Canadian federal government announced revised immigration targets, planning to reduce the proportion of temporary foreign workers and international students over the next three years.", "Real"),
    ("The World Bank approved an additional 1.5 billion dollar development assistance package to support energy infrastructure reconstruction and social services across regional municipalities.", "Real"),
    ("The United States Postal Service announced the upcoming implementation of new automated sorting machinery designed to streamline parcel delivery and reduce operating losses.", "Real"),
    ("Health Canada issued a consumer advisory warning against counterfeit medications distributed through unlicensed online pharmacies operating outside domestic regulatory oversight.", "Real"),
    ("The European Space Agency's Euclid space observatory transmitted its first full-color astronomical images, capturing sharp wide-angle views of thousands of galaxies across the Perseus cluster.", "Real"),
    ("The Department of the Interior finalized a public lands rule putting conservation and habitat restoration on equal regulatory footing with oil extraction and livestock grazing.", "Real"),
    ("The Nobel Memorial Prize in Economic Sciences was awarded to Harvard University professor Claudia Goldin for her pioneering historical research on women's earnings and labor market outcomes.", "Real"),
    ("A team of marine biologists discovered a vibrant, previously undocumented deep-sea coral reef ecosystem spanning more than two miles along the Galapagos Islands volcanic ridge.", "Real"),
    ("The US Department of Agriculture authorized the commercial sale of cultivated cell-cultured chicken, permitting two California startups to begin restaurant distribution.", "Real"),
    ("The World Health Organization ratified a revised version of the International Health Regulations to strengthen global readiness against future cross-border pandemic threats.", "Real"),
    ("The National Highway Traffic Safety Administration opened a preliminary safety investigation into automated driving systems following reports of intersection collisions.", "Real"),
    ("The Nobel Prize in Physiology or Medicine was awarded to Katalin Kariko and Drew Weissman for discoveries concerning nucleoside base modifications that enabled effective mRNA vaccines.", "Real"),

    # FAKE / CONSPIRACY NEWS EXAMPLES
    ("SHOCKING: Secret United Nations blueprint proves global elites are secretly installing microchips in tap water pipes to remotely control human thoughts using 5G radio towers!", "Fake"),
    ("BREAKING: Leaked documents expose that NASA faked every space mission and the Earth is actually encased in a giant glass dome guarded by international military warships in Antarctica.", "Fake"),
    ("Miracle secret cure uncovered: Eating crushed lemon peels with raw garlic completely cures stage 4 cancer in 24 hours, but pharmaceutical executives bribed judges to ban the remedy!", "Fake"),
    ("Bombshell military tribunal confirms all world leaders were replaced by shape-shifting reptilian clones during the recent World Economic Forum summit in Switzerland.", "Fake"),
    ("URGENT ALERT: Government introduces mandatory barcodes stamped on citizens' foreheads under top-secret martial law executive order signed yesterday at midnight!", "Fake"),
    ("CONFIRMED: COVID-19 pandemic was orchestrated by time travelers using artificial wireless frequency pulses to deactivate the human immune system and force digital currency adoption.", "Fake"),
    ("Scientific conspiracy exposed: Scientists secretly admit that gravity does not exist and everything is held down by dense atmospheric pressure generated by giant subterranean fans.", "Fake"),
    ("EMERGENCY NOTICE: Drinking two cups of boiled kerosene cleanses all microplastics and synthetic mRNA proteins from your blood instantly with zero side effects!", "Fake"),
    ("EXPOSED: Pope Francis arrested by Interpol agents in Rome on secret fraud charges and replaced with an artificial intelligence holographic projection broadcasted on Vatican TV.", "Fake"),
    ("LEAKED VIDEO: Secret underground bunker beneath Denver Airport housing millions of alien extraterrestrial specimens caught on camera by patriotic whistleblower before mysterious disappearance.", "Fake"),
    ("BOMBSHELL: Drinking colloidal silver daily makes humans immortal and immune to all known viral infections, but corrupt health agencies hide the truth to protect profits!", "Fake"),
    ("SHOCKING REVELATION: Federal Reserve building completely empty as billionaires secretly evacuated all gold reserves to hidden bunkers on the dark side of Mars.", "Fake"),
    ("ALERT: Commercial airplanes are spraying dangerous mind-control chemicals known as chemtrails to permanently sterilize the population and suppress human intelligence.", "Fake"),
    ("UNBELIEVABLE: Bill Gates admits in live interview that wireless phone batteries contain dormant virus capsules programmed to release toxins when activated by satellite signals.", "Fake"),
    ("PROOF: The Moon is an artificial metallic surveillance satellite operated by ancient secret societies to beam hypnotic audio waves into human dreams every night.", "Fake"),
    ("CONFIDENTIAL REPORT: Five hundred congressmen secretly convicted in military tribunal for treason and replaced with lookalike actors using high-tech silicon masks.", "Fake"),
    ("MIRACLE DISCOVERY: Staring directly into the midday sun for three hours every morning cleanses your pineal gland and eliminates the need to eat food or drink water forever.", "Fake"),
    ("SECRET MEMO: Central banks plan to confiscate all private checking accounts next Tuesday and replace physical currency with social credit chips implanted in wrists.", "Fake"),
    ("BOMBSHELL: Prehistoric frozen woolly mammoths discovered alive in hidden tropical valley underneath Greenland ice sheet being kept secret by military scientists.", "Fake"),
    ("EXPOSED: High-voltage microwave towers were responsible for sinking the Titanic in 1912 as part of an early financial cabal plan to establish the Federal Reserve system.", "Fake"),
    ("URGENT: Vaccines contain synthetic bioluminescent nanobots that emit unique Bluetooth MAC addresses readable by any nearby smartphone scanner, shocking video shows.", "Fake"),
    ("ALERT: Government climate scientists secretly admitted in leaked emails that polar ice caps are growing at record speed and global warming was completely invented to collect taxes.", "Fake"),
    ("BREAKING: Famous Hollywood celebrity reveals that drinking raw unpasteurized river water provides complete natural immunity against all diseases known to modern science.", "Fake"),
    ("SCANDAL: Major retail stores caught spraying invisible hypnotizing pheromones through air conditioning vents to compel shoppers to spend thousands of dollars uncontrollably.", "Fake"),
    ("LEAKED AUDIO: Leading pharmaceutical CEO confesses that all chronic diseases were manufactured in corporate laboratories to generate trillion-dollar prescription sales.", "Fake"),
    ("SHOCK REPORT: Ancient pyramid power generators discovered beneath the Grand Canyon capable of providing free wireless electricity to the entire world, suppressed by energy cartels.", "Fake"),
    ("WARNING: Microwave ovens alter the molecular structure of water turning healthy food into deadly radiation poison that causes immediate cardiovascular failure.", "Fake"),
    ("CONFIRMED: Secret subterranean tunnels connecting all national capitals discovered by independent truckers exposing global underground child smuggling ring.", "Fake"),
    ("TERRIFYING TRUTH: Smart electric meters installed on suburban homes are secretly listening to private bedroom conversations and transmitting audio files to foreign governments.", "Fake"),
    ("BREAKING: World Health Organization passes secret treaty allowing foreign military troops to enter private homes and forcibly quarantine citizens who refuse dietary guidelines.", "Fake"),
    ("AMAZING MIRACLE: Rubbing raw potato slices on your temples cures Alzheimer's disease within one week according to suppressed Soviet medical experiments.", "Fake"),
    ("EXPOSED: Artificial snow falling across Midwestern states does not melt under a lighter flame and turns black, proving weather modification geoengineering chemical warfare.", "Fake"),
    ("ALERT: Secret executive order authorizes federal agents to seize all home vegetable gardens to force citizens into purchasing government-approved synthetic processed paste.", "Fake"),
    ("BOMBSHELL: Space agencies admit astronauts never left low Earth orbit because radiation belts are an impassable wall of fire created by ancient deities.", "Fake"),
    ("UNFILTERED TRUTH: Drinking warm salt water mixed with baking soda cures diabetes in three days by neutralizing all acidic toxins stored in the pancreas.", "Fake"),
    ("SHOCKING: Global financial elites caught gathering in remote forest performing bizarre rituals to sacrifice fiat currencies and usher in one-world digital dictatorship.", "Fake"),
    ("SECRET REVEALED: Toothpaste fluoridation is a top-secret psychological experiment implemented in 1950 to make the general population docile and obedient to authority.", "Fake"),
    ("BREAKING NEWS: Secret satellite imagery shows massive subterranean flying saucer fleet emerging from ocean depths off the coast of California.", "Fake"),
    ("EXPOSED: Smartphone cameras secretly take photos of users every five seconds and upload biometric scans directly to secret intelligence cloud servers.", "Fake"),
    ("URGENT ALERT: Major food manufacturers caught injecting human fetal cells into breakfast cereals to enhance artificial flavor profiles according to whistleblower testimony.", "Fake"),
]

def main():
    target_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "news_sample.csv")
    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        for text, label in DATA:
            writer.writerow([text, label])
    print(f"Generated {len(DATA)} sample news records in {target_path}")

if __name__ == "__main__":
    main()
