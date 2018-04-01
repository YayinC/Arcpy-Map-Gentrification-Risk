# Import necessary modules
import sys, os, string, math, arcpy, traceback,numpy
from arcpy import env
from arcpy.sa import *

# Allow output file to overwrite any existing file of the same name
arcpy.env.overwriteOutput = True

try:
    censusbdry = arcpy.GetParameterAsText(0)
    totalpop = arcpy.GetParameterAsText(1)
    nonwhite = arcpy.GetParameterAsText(2)
    popover25 = arcpy.GetParameterAsText(3)
    bach = arcpy.GetParameterAsText(4)
    totalHH = arcpy.GetParameterAsText(5)
    renters = arcpy.GetParameterAsText(6)
    medianInc = arcpy.GetParameterAsText(7)
    stations = arcpy.GetParameterAsText(8)
    busstops = arcpy.GetParameterAsText(9)
    parks = arcpy.GetParameterAsText(10)
    stores = arcpy.GetParameterAsText(11)
    neighborhood = arcpy.GetParameterAsText(12)
    GentrificationRisk = arcpy.GetParameterAsText(13)
    censusid = arcpy.GetParameterAsText(14)
    neighborhoodid = arcpy.GetParameterAsText(15)
    outTable = arcpy.GetParameterAsText(16)

    OutputShapefile = GentrificationRisk[:-4] + "_demo" + ".shp"
    arcpy.Copy_management(censusbdry, OutputShapefile)
    totalSC = "totalSC"
    arcpy.AddField_management(OutputShapefile, totalSC, "SHORT")

    def calculate_sum_value(table, field):
        na = arcpy.da.TableToNumPyArray(table, field)
        return numpy.sum(na[field])

    def calculate_mean_value(table, field):
        na = arcpy.da.TableToNumPyArray(table, field)
        return numpy.mean(na[field])

    total_pop = calculate_sum_value(censusbdry, totalpop)
    total_nonwhite = calculate_sum_value(censusbdry, nonwhite)
    total_over25 = calculate_sum_value(censusbdry,popover25)
    total_bach = calculate_sum_value(censusbdry,bach)
    total_HH = calculate_sum_value(censusbdry,totalHH)
    total_renters = calculate_sum_value(censusbdry,renters)

    mean_income = calculate_mean_value(censusbdry,medianInc)
    nonwh_p = total_nonwhite/total_pop
    bach_p = total_bach/total_over25
    renter_p = total_renters/total_HH

    enumerationOfRecords = arcpy.UpdateCursor(OutputShapefile)

    for record in enumerationOfRecords:
        NonWhite = record.getValue(nonwhite)
        TotPop = record.getValue(totalpop)
        BachMore = record.getValue(bach)
        PopOver25 = record.getValue(popover25)
        OccHHs = record.getValue(totalHH)
        Renters = record.getValue(renters)
        MedIncome = record.getValue(medianInc)
    #Calculate location quotients using the percentage on city level, which is calculated based on the output summary table
        if TotPop == 0:
            continue;
        else:
            LQ_non_white = NonWhite / (nonwh_p*TotPop)
            LQ_bachmore = BachMore / (bach_p*PopOver25)
            LQ_renters = Renters / (renter_p*OccHHs)

    # Reclass
        if (LQ_non_white<=0.8):
            nonwhiteScore = 0
        elif(LQ_non_white>0.8 and LQ_non_white<=1.2):
            nonwhiteScore = 1
        elif(LQ_non_white>1.2 and LQ_non_white<=1.5):
            nonwhiteScore = 2
        else:
            nonwhiteScore = 3

        if (LQ_bachmore<=0.8):
            bachmoreScore = 3
        elif(LQ_bachmore>0.8 and LQ_bachmore<=1.2):
            bachmoreScore = 2
        elif(LQ_bachmore>1.2 and LQ_bachmore<=1.5):
            bachmoreScore = 1
        else:
            bachmoreScore = 0

        if (LQ_renters<=0.8):
            renterSC = 0
        elif(LQ_renters>0.8 and LQ_renters<=1.2):
            renterSC = 1
        elif(LQ_renters>1.2 and LQ_renters<=1.5):
            renterSC = 2
        else:
            renterSC = 3

        if (MedIncome<= mean_income*0.6):
            incomeScore = 3
        elif(MedIncome> mean_income*0.6 and MedIncome<= mean_income*0.8):
            incomeScore = 2
        elif(MedIncome> mean_income*0.8 and MedIncome<= mean_income*1.2):
            incomeScore = 1
        else:
            incomeScore = 0

        totalSCORE = nonwhiteScore+bachmoreScore+renterSC+incomeScore
        record.setValue(totalSC, totalSCORE)
        enumerationOfRecords.updateRow(record)

    del record
    del enumerationOfRecords

    arcpy.env.workspace = "C:/Users/yayin_cai/Documents/ArcGIS/Default.gdb"
    demoScore = GentrificationRisk[:-4] + "_demoScore"+".tif"
    arcpy.FeatureToRaster_conversion(OutputShapefile,"totalSC",demoScore, "")

    # Check out the ArcGIS Spatial Analyst extension license
    arcpy.CheckOutExtension("Spatial")

    # Calculate distance to amenities
    SubwayDistance = EucDistance(stations, "", "", "")
    subwayScore = arcpy.sa.Reclassify(SubwayDistance, "Value",
                                   RemapRange([[0, 1320, 3], [1320, 2640, 2], [2640, 3960, 1], [3960, 500000, 0]]),
                                   "DATA")

    ParkDistance = EucDistance(parks, "", "", "")
    parkScore = arcpy.sa.Reclassify(ParkDistance, "Value",
                                    RemapRange([[0, 2640, 2], [2640, 5280, 1], [5280, 500000, 0]]), "DATA")

    GroStoreDistance = EucDistance(stores, "", "", "")
    storeScore = arcpy.sa.Reclassify(GroStoreDistance, "Value", RemapRange([[0, 1320, 1], [1320, 500000, 0]]), "DATA")

    BusDistance = EucDistance(busstops, "", "", "")
    busScore = arcpy.sa.Reclassify(BusDistance, "Value", RemapRange([[0, 1320, 1], [1320, 500000, 0]]), "DATA")

    # Spatial join the census tracts to itself to see the census tracts intersecting with each one
    InputShapefile_COPY = GentrificationRisk[:-4] + "_inputcopy" + ".shp"
    spatialjoin = GentrificationRisk[:-4] + "_join" + ".shp"
    arcpy.Copy_management(censusbdry, InputShapefile_COPY)
    arcpy.SpatialJoin_analysis(censusbdry, InputShapefile_COPY, spatialjoin, "JOIN_ONE_TO_MANY", "", "", "INTERSECT",
                               "", "")
    spatialjoinNear = GentrificationRisk[:-4] + "_joinNear" + ".shp"
    arcpy.Copy_management(spatialjoin, spatialjoinNear)
    neighbors_score = "neighbors"
    arcpy.AddField_management(spatialjoinNear, neighbors_score, "SHORT")

    # Find those census tracts whose median household income is low but the neighbors' is high
    enumerationOfRecords2 = arcpy.UpdateCursor(spatialjoinNear)
    for item in enumerationOfRecords2:
        income = item.getValue(medianInc)
        neighbors = item.getValue(medianInc)
        if (income <= mean_income* 0.8 and neighbors > mean_income*1.2):
            score = 1
        else:
            score = 0
        item.setValue(neighbors_score, score)
        enumerationOfRecords2.updateRow(item)

    del item
    del enumerationOfRecords2

  #Dissolve the shapefile by unique id
    dis_output = GentrificationRisk[:-4]+"_dis" + ".shp"
    arcpy.Dissolve_management(spatialjoinNear, dis_output, censusid, [["neighbors","MAX"]],"","")

    neighborScore =  GentrificationRisk[:-4] + "_nearScore"+ ".tif"
    arcpy.FeatureToRaster_conversion(spatialjoinNear,"neighbors",neighborScore, "")

    #Calculate total score which indicates the risk of gentrification
    totalscore=demoScore+subwayScore+parkScore+storeScore+busScore+neighborScore
    totalscore.save(GentrificationRisk)

    outZSaT = ZonalStatisticsAsTable(neighborhood,neighborhoodid, totalscore,
                                     outTable, "NODATA", "MEAN")

    arcpy.Delete_management(OutputShapefile)
    arcpy.Delete_management(demoScore)
    arcpy.Delete_management(InputShapefile_COPY)
    arcpy.Delete_management(spatialjoin)
    arcpy.Delete_management(spatialjoinNear)
    arcpy.Delete_management(dis_output)
    arcpy.Delete_management(neighborScore)

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.message )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")