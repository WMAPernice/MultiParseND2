DIR = getDirectory("select the input folder");
targetFolder = getDirectory("select the output folder");
files = getFileList(DIR);
Channel_order = "2,3,1,4"
Min_IMSIZE = 512;
constrain = " ";

setBatchMode(true);

print("Starting new resize and Channel order session...");
for (i=0; i<files.length; i++) {
	if (endsWith(files[i], ".tiff")) { 
		open(DIR + files[i]);
		getDimensions(width, height, channels, slices, frames);
		origTitle = getTitle();
		split_Title = split(origTitle, ".");
		Im_id = split_Title[0];
		run("Make Substack...", " slices="+Channel_order);
		
		//run("Images to Stack", "name=[Stack]");
		run("Size...", "width=&Min_IMSIZE height=&Min_IMSIZE" +constrain+ "average interpolation=Bicubic");
		saveAs("tiff", targetFolder + "/" + Im_id + ".tiff");
		run("Close All");
		
	}
}
print("all done!");
setBatchMode("exit & display");
