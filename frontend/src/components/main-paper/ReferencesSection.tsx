/**
 * PATH: frontend/src/components/main-paper/ReferencesSection.tsx
 * PURPOSE: References list section of the Main Paper.
 * WHY: Extracted from MainPaper.tsx to keep the parent under 300 lines.
 * DEPENDENCIES:
 *  - lucide-react FileText: section icon
 *  - Citation/ReferencesList: renders formatted academic references
 *  - ui/card: Card + CardContent wrappers
 */

import { FileText } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { ReferencesList } from "@/components/Citation"

export function ReferencesSection() {
  return (
    <section id="references" className="scroll-mt-24">
      <div className="flex items-center gap-3 mb-4">
        <FileText className="h-5 w-5 text-primary" />
        <h2 className="text-2xl font-bold">References</h2>
      </div>
      <Card className="bg-card">
        <CardContent className="pt-6">
          <ReferencesList
            ids={[
              "fasb_sfas2_1974",
              "lev_sougiannis_1996",
              "chan_lakonishok_sougiannis_2001",
              "eberhart_maxwell_siddique_2004",
              "hirshleifer_hsu_li_2013",
              "cai_cooper_he_2023",
              "kothari_laguerre_leone_2002",
              "griliches_1981",
              "griliches_1990",
              "hall_jaffe_trajtenberg_2005",
              "deng_lev_narin_1999",
              "gu_2005",
              "li_2011",
              "barth_kasznik_mcnichols_2001",
              "fama_french_1993",
              "fama_french_2015",
              "fama_macbeth_1973",
              "carhart_1997",
              "hou_xue_zhang_2015",
              "hou_mo_xue_zhang_2022",
              "asness_frazzini_2013",
              "amihud_2002",
              "novy_marx_velikov_2016",
              "ahmed_bu_ye_2025",
              "newey_west_1987",
              "barney_1991",
              "porter_1992",
              "cohen_klepper_1996",
              "polk_sapienza_2009",
              "jaffe_1986",
              "jagannathan_korajczyk_wang_2025",
            ]}
          />
        </CardContent>
      </Card>
    </section>
  )
}
