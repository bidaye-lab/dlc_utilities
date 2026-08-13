%% get all files (separated by folder/file into separate structure cells)
fileName = struct2cell(dir('Z:\...\Genotype\BallTracking\*.mat'));
smoothwin = 20
% construct all file pa
% ths and save each to cell array
allFiles = [];
arr_size = size(fileName);
for i=1:arr_size(2)
    temp_file = fileName{1,i};
    temp_folder = fileName{2,i};
    allFiles = [allFiles, strcat(temp_folder,"\", temp_file)];
end

%% load buffer data

% bufferData = readtable("Z:\BallSystem_AniposeReconstructions\10_individual_calib\4_ES_HB_2.0\Pooled\ES_HB_Metadata_buffer.xlsx");
% stimFreq = readtable("Z:\BallSystem_AniposeReconstructions\45_IntSampling_Stops_20xCsChrim\NEW\project\FG_higher\BallTracking_renamed\Metadata_intensity.xlsx");

%% get data 
all_flies = [];
for i=1:length(allFiles)
    curr_fly = allFiles(i);
    videoDuration = 3500;

    % get current fly'
    curr_flyspl = split(curr_fly, "_");
    curr_flyspl = curr_flyspl(end-1);
    curr_flyspl = split(curr_flyspl, ".");
    curr_fly_num = curr_flyspl(1);
    disp(curr_fly_num)
    all_flies = [all_flies curr_fly_num];
% 
%     curr_fly_bf = bufferData.(curr_fly_num) - 1; % subtract 1 due to data collection
%     curr_fly_bf = curr_fly_bf(~isnan(curr_fly_bf));
   
%     extract all velocity data
%     [timeArr_vel, x_vel, y_vel, z_vel] = extract_all_vel_data(curr_fly, curr_fly_bf);
    [timeArr_vel, x_vel, y_vel, z_vel] = extract_all_vel_data(curr_fly, smoothwin);
    ballvel_table = table(x_vel, y_vel, z_vel);
    writetable(ballvel_table, join(["Z:\...\Genotype\BallVel\", string(curr_fly_num), "ballvel.csv"], '')); % change to relevant file path

end

%% extract all data for velocity

% function [timeArr, forward_x, sideways_y, angVel_z] = extract_all_vel_data(fileName, curr_fly_bf)
function [timeArr, forward_x, sideways_y, angVel_z] = extract_all_vel_data(fileName, smoothwin)

    BallTrack = matfile(fileName);
    disp(fileName)
    
    BallStruct = BallTrack.sensorData;
    ballRotations = BallStruct.bufferRotations;

    ballRotations = ballRotations(all(~isnan(ballRotations),2),:);

    ballRotationX = ballRotations(:,1)';
    ballRotationXUp = interp(ballRotationX,4);
    ballRotationY = ballRotations(:,2)';
    ballRotationYUp = interp(ballRotationY,4);
    ballRotationZ = ballRotations(:,3)';
    ballRotationZUp = interp(ballRotationZ,4);

    display(length(ballRotationX))
    display(length(ballRotationXUp))

%     [ballRotationXUp, ballRotationYUp, ballRotationZUp] = filter_buffers_vel(ballRotationXUp, ballRotationYUp, ballRotationZUp, curr_fly_bf);

    timeArr = 1:length(ballRotationZUp);
    forward_x=smoothdata(ballRotationXUp,"gaussian",smoothwin)';
    sideways_y=smoothdata(ballRotationYUp,"gaussian",smoothwin)';
    angVel_z=smoothdata(ballRotationZUp,"gaussian",smoothwin)';
    
end

%% filter buffer frames : velocity
function [ballRotationXUp, ballRotationYUp, ballRotationZUp] = filter_buffers_vel(ballRotationXUp, ballRotationYUp, ballRotationZUp, curr_fly_bf)


    extra_frames = length(ballRotationXUp)-(1400*length(curr_fly_bf))-sum(curr_fly_bf);
    display("extra frames: "+ extra_frames)
    display("original upsampled length: "+ length(ballRotationXUp))
    display("no. of frames to remove: "+ sum(curr_fly_bf))

    for i=1:length(curr_fly_bf)

        first = ((i-1)*1400)+1;
        final = ((((i-1)*1400))+curr_fly_bf(i));

        ballRotationXUp(first:final) = [];
        ballRotationYUp(first:final) = [];
        ballRotationZUp(first:final) = [];
    end

    
    if extra_frames > 0
        ballRotationXUp = ballRotationXUp(1:end-extra_frames);
        ballRotationYUp = ballRotationYUp(1:end-extra_frames);
        ballRotationZUp = ballRotationZUp(1:end-extra_frames);
    end

    if extra_frames < 0
        display("length before resampling: "+ length(ballRotationXUp))
        ballRotationXUp = resample(ballRotationXUp, 14000, length(ballRotationXUp));
        ballRotationYUp = resample(ballRotationYUp, 14000, length(ballRotationYUp));
        ballRotationZUp = resample(ballRotationZUp, 14000, length(ballRotationZUp));
        
    end

    display("post-processing length: "+ length(ballRotationXUp))

end

